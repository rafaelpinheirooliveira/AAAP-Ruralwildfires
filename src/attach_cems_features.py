"""Build lagged CEMS features for exploratory, retrospective experiments.

Usage:
    python src/attach_cems_features.py --test
    python src/attach_cems_features.py
    python src/attach_cems_features.py --dry-run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/config.yaml"
CEMS_DIR = ROOT / "data/processed/cems_by_municipality"
OUT = ROOT / "data/processed/cems_features.parquet"
TEST_OUT = ROOT / "data/processed/cems_features_2017-08_test.parquet"

CEMS_VARIABLES = [
    "feat_cems_bui", "feat_cems_dc", "feat_cems_dmc", "feat_cems_ffmc",
    "feat_cems_dsr", "feat_cems_fwi", "feat_cems_isi",
]
FEATURES_CEMS_LAGGED = [
    f"{feature}_{suffix}"
    for feature in CEMS_VARIABLES
    for suffix in ("lag1", "mean_3d", "max_3d", "mean_7d", "max_7d")
]
KEYS = ["date", "cod_concelho"]


def _read_aggregates(paths: list[Path]) -> pd.DataFrame:
    frames = [
        pd.read_parquet(path, columns=KEYS + ["valid_time_utc", *CEMS_VARIABLES])
        for path in paths
    ]
    data = pd.concat(frames, ignore_index=True)
    if data.duplicated(KEYS).any():
        duplicates = int(data.duplicated(KEYS).sum())
        raise ValueError(f"Encontradas {duplicates} datas-concelho CEMS duplicadas.")
    data["date"] = pd.to_datetime(data["date"]).dt.normalize()
    data["cod_concelho"] = data["cod_concelho"].astype(str).str.zfill(4)
    data["valid_time_utc"] = pd.to_datetime(data["valid_time_utc"], utc=True)
    data = data.sort_values(KEYS, kind="stable").reset_index(drop=True)
    return data


def _validate_daily_coverage(data: pd.DataFrame) -> None:
    dates = pd.DatetimeIndex(data["date"].drop_duplicates().sort_values())
    if len(dates) == 0:
        raise ValueError("Não há datas CEMS para processar.")
    if data["cod_concelho"].nunique() != 278:
        raise ValueError(
            f"Esperava 278 concelhos CEMS, encontrei {data['cod_concelho'].nunique()}."
        )
    expected = pd.date_range(dates[0], dates[-1], freq="D")
    if not dates.equals(expected):
        missing = expected.difference(dates)
        raise ValueError(
            "A série CEMS tem dias em falta; não é seguro calcular lags por linha. "
            f"Primeiras datas em falta: {[str(value.date()) for value in missing[:5]]}"
        )
    expected_rows = len(expected) * data["cod_concelho"].nunique()
    if len(data) != expected_rows:
        raise ValueError(
            f"Cobertura irregular: {len(data)} linhas, esperadas {expected_rows} "
            "para todas as datas e concelhos."
        )


def build_features(data: pd.DataFrame) -> pd.DataFrame:
    """Map each target day to CEMS from d-1 and prior complete rolling windows."""
    _validate_daily_coverage(data)
    result = data[KEYS].copy()
    grouped = data.groupby("cod_concelho", sort=False)
    result["cems_source_date_lag1"] = grouped["date"].shift(1)
    result["cems_source_valid_time_utc_lag1"] = grouped["valid_time_utc"].shift(1)

    for feature in CEMS_VARIABLES:
        result[f"{feature}_lag1"] = grouped[feature].shift(1).to_numpy()
        for window in (3, 7):
            prior = grouped[feature].transform(
                lambda values: values.shift(1).rolling(window, min_periods=window).mean()
            )
            result[f"{feature}_mean_{window}d"] = prior.to_numpy()
            prior_max = grouped[feature].transform(
                lambda values: values.shift(1).rolling(window, min_periods=window).max()
            )
            result[f"{feature}_max_{window}d"] = prior_max.to_numpy()

    expected_source_date = result["date"] - pd.Timedelta(days=1)
    valid_source = result["cems_source_date_lag1"].notna()
    if not result.loc[valid_source, "cems_source_date_lag1"].eq(
        expected_source_date.loc[valid_source]
    ).all():
        raise ValueError("O valor CEMS associado a d não corresponde ao dia anterior d−1.")
    if not set(FEATURES_CEMS_LAGGED) <= set(result.columns):
        raise AssertionError("Nem todas as features CEMS esperadas foram construídas.")
    return result


def _input_paths(test: bool) -> list[Path]:
    if test:
        return [CEMS_DIR / "cems_fire_2017-08_test_municipalities.parquet"]
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    start = config["study_period"]["start"].year
    end = config["study_period"]["end"].year
    return [
        CEMS_DIR / f"cems_fire_{year}_municipalities.parquet"
        for year in range(start, end + 1)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test", action="store_true",
        help="constrói features apenas para o mês de teste de agosto de 2017",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="lista os ficheiros esperados sem os ler",
    )
    args = parser.parse_args()

    paths = _input_paths(args.test)
    missing = [path for path in paths if not path.is_file()]
    if missing:
        names = ", ".join(path.name for path in missing)
        if args.dry_run:
            print(f"Faltam {len(missing)} agregações: {names}")
            return
        raise SystemExit(f"Faltam agregações municipais CEMS: {names}")

    target = TEST_OUT if args.test else OUT
    print(f"{len(paths)} ficheiros -> {target.relative_to(ROOT)}")
    if args.dry_run:
        return

    features = build_features(_read_aggregates(paths))
    target.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(target, index=False)
    report = {
        "rows": len(features),
        "municipalities": int(features["cod_concelho"].nunique()),
        "date_start": str(features["date"].min().date()),
        "date_end": str(features["date"].max().date()),
        "features": FEATURES_CEMS_LAGGED,
        "missing_values_by_feature": {
            feature: int(features[feature].isna().sum())
            for feature in FEATURES_CEMS_LAGGED
        },
        "source_date_lag1_verified": True,
        "operational_availability_claimed": False,
    }
    target.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"{len(features):,} linhas; {report['municipalities']} concelhos; "
        f"{report['date_start']} a {report['date_end']}"
    )


if __name__ == "__main__":
    main()
