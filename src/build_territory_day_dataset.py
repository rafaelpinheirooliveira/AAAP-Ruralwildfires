"""Constrói o dataset concelho x dia (Tarefas 1 e 2, momento A = 23:59 de d-1).

Entrada : data/processed/sgif_clean.parquet     (saída de clean_sgif.py)
Saída   : data/processed/territory_day.parquet  (+ territory_day_report.json)

Uma linha = um concelho num dia d. A grelha é completa: contém todos os dias do
período de estudo, com e sem incêndios (dias sem registo são os negativos).

Alvos (construídos com informação do dia d; nunca são features):
  y_fire             1 se houve pelo menos um incêndio no concelho no dia d
  y_fire_no_zero     idem, ignorando registos com área ardida = 0 (sensibilidade)
  y_sig_amin<A>      1 se algum incêndio do dia d teve área final >= A ha

Features (conhecidas às 23:59 de d-1), prefixo `feat_`:
  * calendário do dia d (conhecido de antemão);
  * histórico do concelho até d-1.

Regra anti-leakage do histórico de ÁREA: a área final de um incêndio só é
conhecida quando ele se extingue. Por isso as features de área usam a data de
EXTINÇÃO (e não a de alerta): um incêndio ainda ativo às 23:59 de d-1 não
contribui com a sua área, apenas com a sua contagem (o alerta já é conhecido).

As variáveis meteorológicas (CEMS) serão acrescentadas quando a fonte estiver
confirmada; ainda não fazem parte deste dataset.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data/processed/sgif_clean.parquet"
OUT = ROOT / "data/processed/territory_day.parquet"
REPORT = ROOT / "data/processed/territory_day_report.json"
CONFIG = ROOT / "configs/config.yaml"

WARMUP_DAYS = 30        # janela mais longa do histórico
NO_FIRE_CAP = 365       # valor de days_since_last_fire quando não há incêndio anterior

FEATURES_AT_2359 = [
    "feat_mes", "feat_dia_do_ano", "feat_dia_da_semana",
    "feat_n_incendios_1d", "feat_n_incendios_7d", "feat_n_incendios_30d",
    "feat_dias_desde_ultimo_incendio",
    "feat_area_extinta_30d_ha", "feat_area_max_extinta_30d_ha",
]
TARGET_COLUMNS_PREFIXES = ("y_", "target_only_")


def load_config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def window_before(m: pd.DataFrame, w: int, how: str) -> np.ndarray:
    """Agrega os w dias anteriores a d (d-w .. d-1), excluindo o próprio dia d."""
    r = m.rolling(w, min_periods=1)
    r = r.sum() if how == "sum" else r.max()
    return r.shift(1).fillna(0).to_numpy()


def build(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    start = pd.Timestamp(cfg["study_period"]["start"])
    end = pd.Timestamp(cfg["study_period"]["end"])
    amins = sorted({cfg["amin_main"], *cfg["amin_sensitivity"]})
    days = pd.date_range(start, end)
    conc = np.array(sorted(df["cod_concelho"].unique()))
    D, C = len(days), len(conc)

    alert_day = (df["DataHoraAlerta"].dt.normalize() - start).dt.days.to_numpy()
    c_idx = np.searchsorted(conc, df["cod_concelho"].to_numpy(dtype=str))
    area = df["AreaTotal_ha"].to_numpy(dtype="float32")
    ok = (alert_day >= 0) & (alert_day < D)
    alert_day, c_idx, area = alert_day[ok], c_idx[ok], area[ok]

    # --- matrizes dia x concelho (por data de ALERTA) -------------------------
    n = np.zeros((D, C), dtype="int32")
    n_pos = np.zeros((D, C), dtype="int32")
    max_a = np.zeros((D, C), dtype="float32")
    tot_a = np.zeros((D, C), dtype="float32")
    np.add.at(n, (alert_day, c_idx), 1)
    np.add.at(n_pos, (alert_day, c_idx), (area > 0).astype("int32"))
    np.maximum.at(max_a, (alert_day, c_idx), area)
    np.add.at(tot_a, (alert_day, c_idx), area)

    # --- matrizes dia x concelho (por data de EXTINÇÃO, para a área) ----------
    ext = df.loc[ok, "DataHora_Extincao"]
    has_ext = ext.notna().to_numpy()
    ext_day = ((ext.dt.normalize() - start).dt.days.fillna(-1)).to_numpy().astype(int)
    ext_ok = has_ext & (ext_day >= 0) & (ext_day < D)
    ext_sum = np.zeros((D, C), dtype="float32")
    ext_max = np.zeros((D, C), dtype="float32")
    np.add.at(ext_sum, (ext_day[ext_ok], c_idx[ext_ok]), area[ext_ok])
    np.maximum.at(ext_max, (ext_day[ext_ok], c_idx[ext_ok]), area[ext_ok])

    # --- histórico até d-1 -------------------------------------------------------
    mn = pd.DataFrame(n)
    hist_1d = mn.shift(1).fillna(0).to_numpy()
    hist_7d = window_before(mn, 7, "sum")
    hist_30d = window_before(mn, 30, "sum")
    has_fire = np.where(n > 0, np.arange(D)[:, None], np.nan)
    last = pd.DataFrame(has_fire).ffill().shift(1).to_numpy()
    since = np.where(np.isnan(last), NO_FIRE_CAP, np.arange(D)[:, None] - last)
    since = np.minimum(since, NO_FIRE_CAP)
    area_sum_30 = window_before(pd.DataFrame(ext_sum), 30, "sum")
    area_max_30 = window_before(pd.DataFrame(ext_max), 30, "max")

    # --- verificações anti-leakage (amostra aleatória) ----------------------------
    rng = np.random.default_rng(cfg["seed"])
    for _ in range(2000):
        d, c = int(rng.integers(WARMUP_DAYS, D)), int(rng.integers(0, C))
        assert hist_1d[d, c] == n[d - 1, c]
        assert hist_7d[d, c] == n[d - 7:d, c].sum()
        assert hist_30d[d, c] == n[d - 30:d, c].sum()
        assert abs(area_sum_30[d, c] - ext_sum[d - 30:d, c].sum()) < 1e-2
        assert since[d, c] >= 1  # nunca usa o próprio dia d

    # --- tabela longa (ordem: data, depois concelho) -----------------------------
    flat = lambda a, t: a.astype(t).ravel()
    date_col = np.repeat(days.to_numpy(), C)
    out = pd.DataFrame({
        "date": date_col,
        "cod_concelho": pd.Categorical(np.tile(conc, D), categories=conc),
        "cod_distrito": pd.Categorical(np.tile(np.array([c[:2] for c in conc]), D)),
        "feat_mes": np.repeat(days.month.to_numpy(), C).astype("int8"),
        "feat_dia_do_ano": np.repeat(days.dayofyear.to_numpy(), C).astype("int16"),
        "feat_dia_da_semana": np.repeat(days.dayofweek.to_numpy(), C).astype("int8"),
        "feat_n_incendios_1d": flat(hist_1d, "int16"),
        "feat_n_incendios_7d": flat(hist_7d, "int16"),
        "feat_n_incendios_30d": flat(hist_30d, "int16"),
        "feat_dias_desde_ultimo_incendio": flat(since, "int16"),
        "feat_area_extinta_30d_ha": flat(area_sum_30, "float32"),
        "feat_area_max_extinta_30d_ha": flat(area_max_30, "float32"),
        "flag_warmup": np.repeat((np.arange(D) < WARMUP_DAYS), C),
        "target_only_n_incendios": flat(n, "int16"),
        "target_only_area_max_ha": flat(max_a, "float32"),
        "target_only_area_total_ha": flat(tot_a, "float32"),
        "y_fire": flat(n > 0, "int8"),
        "y_fire_no_zero": flat(n_pos > 0, "int8"),
    })
    for a in amins:
        out[f"y_sig_amin{a:g}"] = flat(max_a >= a, "int8")

    forbidden = [c for c in FEATURES_AT_2359 if c.startswith(TARGET_COLUMNS_PREFIXES)]
    assert not forbidden, "alvo usado como feature"
    assert set(FEATURES_AT_2359) <= set(out.columns)
    return out, {"amins": amins, "dias": D, "concelhos": C}


def main() -> None:
    cfg = load_config()
    df = pd.read_parquet(
        CLEAN, columns=["DataHoraAlerta", "DataHora_Extincao", "cod_concelho", "AreaTotal_ha"]
    )
    out, meta = build(df, cfg)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)

    rep = {"linhas": len(out), **meta, "prevalencia": {}, "por_periodo_pct": {}}
    ycols = [c for c in out.columns if c.startswith("y_")]
    out_y = out[ycols].assign(ano=out["date"].dt.year)
    for c in ycols:
        rep["prevalencia"][c] = {"positivos": int(out[c].sum()),
                                 "pct": round(100 * float(out[c].mean()), 4)}
    per = pd.cut(out_y["ano"], [2000, 2010, 2020, 2025], labels=["2001-2010", "2011-2020", "2021-2025"])
    for c in ycols:
        rep["por_periodo_pct"][c] = {str(k): round(100 * float(v), 4)
                                     for k, v in out_y.groupby(per, observed=True)[c].mean().items()}
    rep["features_23h59"] = FEATURES_AT_2359
    REPORT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{len(out):,} linhas = {meta['dias']} dias x {meta['concelhos']} concelhos")
    for c in ycols:
        p = rep["prevalencia"][c]
        print(f"  {c:16s} positivos={p['positivos']:>8,}  ({p['pct']:.3f}%)")


if __name__ == "__main__":
    main()
