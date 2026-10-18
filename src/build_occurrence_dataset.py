"""Constrói o dataset de ocorrências (Tarefa 3, momento B = DataHoraAlerta).

Entrada : data/processed/sgif_clean.parquet   (saída de clean_sgif.py)
Saída   : data/processed/occurrences.parquet  (+ occurrences_report.json)

Uma linha = uma ocorrência. O alvo `y_sig_amin<A>` vale 1 se a área ardida
final >= A hectares. Os valores de A vêm de configs/config.yaml.

Regra de disponibilidade: só entram como features colunas conhecidas em
`DataHoraAlerta`. A classificação de cada coluna está em FEATURE_GROUPS e é a
única fonte de verdade: os modelos devem importar FEATURES_AT_ALERT daqui.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data/processed/sgif_clean.parquet"
OUT = ROOT / "data/processed/occurrences.parquet"
REPORT = ROOT / "data/processed/occurrences_report.json"
CONFIG = ROOT / "configs/config.yaml"

# --- Classificação das colunas pela disponibilidade ---------------------------
# Features do conjunto principal: conhecidas no instante do alerta.
FEATURES_AT_ALERT = [
    "feat_mes",            # calendário
    "feat_dia_do_ano",
    "feat_dia_da_semana",
    "feat_hora",           # hora do alerta (0-23)
    "feat_cod_distrito",   # localização do ponto de início
    "feat_cod_concelho",
    "feat_latitude",
    "feat_longitude",
    "feat_x_etrs89",
    "feat_y_etrs89",
]

# Disponíveis no alerta, mas com problemas (cobertura variável, ausência
# ambígua, hora de cálculo desconhecida). Ficam fora do conjunto principal e
# entram só em ablações justificadas.
FEATURES_PENDING = [
    "pend_fonte_alerta",   # 100% até 2023, cai para ~78% em 2025
    "pend_rnap",           # 1 se preenchido; vazio = "não aplicável" ou "não registado"
    "pend_rnmpf",          # idem
    "pend_fwi", "pend_dsr", "pend_isi", "pend_dc", "pend_dmc", "pend_ffmc", "pend_bui",
]

# Informação posterior ao alerta: NUNCA entram como features. Só a área final
# é mantida, e apenas para construir o alvo.
LEAKAGE_COLUMNS_DROPPED = [
    "AreaPov_ha", "AreaMato_ha", "AreaAgric_ha", "ClasseArea",
    "DataHora_PrimeiraIntervencao", "DataHora_Extincao", "Duracao_Horas",
    "IncSup24horas", "CodCausa", "TipoCausa", "GrupoCausa", "DescricaoCausa",
]


def load_amins() -> list[float]:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return sorted({cfg["amin_main"], *cfg["amin_sensitivity"]})


def build(df: pd.DataFrame, amins: list[float]) -> pd.DataFrame:
    d = df["DataHoraAlerta"]
    bad_xy = df["flag_coord_invalida"]  # X/Y ETRS89 também são postos a nulo
    out = pd.DataFrame({
        # Identificação e chaves (não são features)
        "codigo_sgif": df["Codigo_SGIF"],
        "data_hora_alerta": d,
        "ano": d.dt.year,
        # Conjunto principal
        "feat_mes": d.dt.month,
        "feat_dia_do_ano": d.dt.dayofyear,
        "feat_dia_da_semana": d.dt.dayofweek,
        "feat_hora": d.dt.hour,
        "feat_cod_distrito": df["cod_distrito"],
        "feat_cod_concelho": df["cod_concelho"],
        "feat_latitude": df["Latitude"],
        "feat_longitude": df["Longitude"],
        "feat_x_etrs89": df["X_ETRS89"].mask(bad_xy),
        "feat_y_etrs89": df["Y_ETRS89"].mask(bad_xy),
        # Pendentes
        "pend_fonte_alerta": df["FonteAlerta"],
        "pend_rnap": df["RNAP"].notna().astype("int8"),
        "pend_rnmpf": df["RNMPF"].notna().astype("int8"),
        "pend_fwi": df["FWI"], "pend_dsr": df["DSR"], "pend_isi": df["ISI"],
        "pend_dc": df["DC"], "pend_dmc": df["DMC"], "pend_ffmc": df["FFMC"],
        "pend_bui": df["BUI"],
        # Apenas para construir o alvo. NÃO usar como feature.
        "target_only_final_burned_area_ha": df["AreaTotal_ha"],
        # Marcas de qualidade (para exclusões testáveis)
        "flag_area_zero": df["flag_area_zero"],
        "flag_coord_invalida": df["flag_coord_invalida"],
        "flag_possivel_duplicado": df["flag_possivel_duplicado"],
    })
    for a in amins:
        label = f"{a:g}"
        out[f"y_sig_amin{label}"] = (df["AreaTotal_ha"] >= a).astype("int8")
    return out.sort_values("data_hora_alerta", kind="stable").reset_index(drop=True)


def main() -> None:
    amins = load_amins()
    occ = build(pd.read_parquet(CLEAN), amins)

    # Salvaguarda: nenhuma feature pode ser uma coluna proibida ou de alvo.
    forbidden = {"target_only_final_burned_area_ha", *LEAKAGE_COLUMNS_DROPPED}
    assert not forbidden & set(FEATURES_AT_ALERT), "feature proibida no conjunto principal"
    assert all(c in occ.columns for c in FEATURES_AT_ALERT + FEATURES_PENDING)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    occ.to_parquet(OUT, index=False)

    rep = {"linhas": len(occ), "periodo": [str(occ.data_hora_alerta.min()), str(occ.data_hora_alerta.max())],
           "amins_ha": amins, "positivos": {}, "prevalencia_pct": {}}
    for a in amins:
        c = f"y_sig_amin{a:g}"
        rep["positivos"][c] = int(occ[c].sum())
        rep["prevalencia_pct"][c] = round(100 * occ[c].mean(), 3)
    rep["features_principais"] = FEATURES_AT_ALERT
    rep["features_pendentes"] = FEATURES_PENDING
    REPORT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(occ)} ocorrências; {len(FEATURES_AT_ALERT)} features principais, "
          f"{len(FEATURES_PENDING)} pendentes.")
    for a in amins:
        c = f"y_sig_amin{a:g}"
        print(f"  {c:16s} positivos={rep['positivos'][c]:>6}  ({rep['prevalencia_pct'][c]:.2f}%)")


if __name__ == "__main__":
    main()
