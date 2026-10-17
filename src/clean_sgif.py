"""Limpeza dos registos de incêndios SGIF (ICNF) 2001-2025.

Entrada : data/raw/Combined_Registos_Incendios_SGIF_2001_2025.xlsx
Saída   : data/processed/sgif_clean.parquet  (+ data/processed/clean_report.json)

Princípios:
  * Nenhum registo é apagado, exceto os que não têm chave de concelho.
  * Os problemas detetados ficam marcados em colunas `flag_*`, para que a
    decisão de os excluir seja explícita e testável nas experiências.
  * A coluna `DataHoraAlerta` é a única fonte de verdade para data e hora.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/Combined_Registos_Incendios_SGIF_2001_2025.xlsx"
OUT = ROOT / "data/processed/sgif_clean.parquet"
REPORT = ROOT / "data/processed/clean_report.json"

DATE_COLS = ["DataHoraAlerta", "DataHora_PrimeiraIntervencao", "DataHora_Extincao"]
# Caixa envolvente aproximada de Portugal continental (graus).
LAT_MIN, LAT_MAX = 36.9, 42.2
LON_MIN, LON_MAX = -9.6, -6.1


def read_xlsx(path: Path, chunk_rows: int = 50_000) -> pd.DataFrame:
    """Lê o xlsx em streaming (o ficheiro tem 142 MB) para poupar memória."""
    wb = load_workbook(path, read_only=True)
    rows = wb.active.iter_rows(values_only=True)
    header = list(next(rows))
    chunks, buf = [], []
    for row in rows:
        buf.append(row)
        if len(buf) == chunk_rows:
            chunks.append(pd.DataFrame(buf, columns=header))
            buf = []
    if buf:
        chunks.append(pd.DataFrame(buf, columns=header))
    wb.close()
    return pd.concat(chunks, ignore_index=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rep: dict = {"linhas_entrada": len(df)}

    # 1. Datas ---------------------------------------------------------
    for c in DATE_COLS:
        antes = df[c].notna().sum()
        # Há dois formatos de texto (com e sem milissegundos): ISO8601 aceita ambos.
        df[c] = pd.to_datetime(df[c], format="ISO8601", errors="coerce")
        rep[f"datas_nao_convertidas_{c}"] = int(antes - df[c].notna().sum())

    # 2. Ano/Mes/Dia/Hora: recalculados a partir de DataHoraAlerta --------
    d = df["DataHoraAlerta"]
    df["flag_hora_inconsistente"] = (
        (d.dt.year != df["Ano"]) | (d.dt.month != df["Mes"])
        | (d.dt.day != df["Dia"]) | (d.dt.hour != df["Hora"])
    )
    rep["registos_ano_mes_dia_hora_inconsistentes"] = int(df["flag_hora_inconsistente"].sum())
    df["Ano"], df["Mes"], df["Dia"], df["Hora"] = d.dt.year, d.dt.month, d.dt.day, d.dt.hour

    # 3. Chave de concelho a partir do DTCCFR (6 dígitos: DDCCFF) ---------
    dtccfr = df["DTCCFR"].astype("Int64").astype("string").str.zfill(6)
    df["cod_distrito"] = dtccfr.str[:2]
    df["cod_concelho"] = dtccfr.str[:4]
    rep["nomes_concelho_brutos"] = int(df["Concelho"].nunique())
    sem_chave = df["cod_concelho"].isna()
    rep["registos_sem_chave_concelho_removidos"] = int(sem_chave.sum())
    df = df.loc[~sem_chave].copy()
    # Nome canónico: a grafia mais frequente para cada código.
    for cod, nome, novo in [("cod_concelho", "Concelho", "concelho"),
                            ("cod_distrito", "Distrito", "distrito")]:
        canon = df.groupby(cod)[nome].agg(lambda s: s.value_counts().index[0])
        df[novo] = df[cod].map(canon)
    rep["concelhos_apos_chave"] = int(df["cod_concelho"].nunique())
    rep["distritos_apos_chave"] = int(df["cod_distrito"].nunique())

    # 4. Coordenadas fora de Portugal continental ------------------------
    fora = ~(df["Latitude"].between(LAT_MIN, LAT_MAX) & df["Longitude"].between(LON_MIN, LON_MAX))
    df["flag_coord_invalida"] = fora
    rep["registos_coord_invalida"] = int(fora.sum())
    df.loc[fora, ["Latitude", "Longitude"]] = pd.NA

    # 5. Área zero ----------------------------------------------------------
    df["flag_area_zero"] = df["AreaTotal_ha"] == 0
    rep["registos_area_zero"] = int(df["flag_area_zero"].sum())
    rep["area_negativa"] = int((df["AreaTotal_ha"] < 0).sum())

    # 6. Possíveis duplicados (mesma freguesia e mesmo minuto de alerta) ---
    df["flag_possivel_duplicado"] = df.duplicated(["DTCCFR", "DataHoraAlerta"], keep=False)
    rep["registos_possivel_duplicado_envolvidos"] = int(df["flag_possivel_duplicado"].sum())
    rep["registos_possivel_duplicado_excedentes"] = int(df.duplicated(["DTCCFR", "DataHoraAlerta"]).sum())

    rep["linhas_saida"] = len(df)
    rep["codigo_sgif_duplicados"] = int(df["Codigo_SGIF"].duplicated().sum())
    return df, rep


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, default=RAW)
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()

    df = read_xlsx(a.raw)
    df, rep = clean(df)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(a.out, index=False)
    REPORT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    for k, v in rep.items():
        print(f"{k:50s} {v}")


if __name__ == "__main__":
    main()
