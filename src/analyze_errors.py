"""Analyze false positives and negatives in held-out wildfire test sets.

The model and threshold are selected on validation by the same routine as
run_experiments.py; this script only characterizes the held-out test errors.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from run_experiments import (
    PROTOCOLS,
    RESULTS,
    _config,
    _feature_set_default,
    _features,
    _load_data,
    _run_fold,
    _splits,
    _target,
)

OUTPUT = RESULTS.parent / "e9_error_analysis.json"


def _reference_record(
    task: int,
    target: str,
    feature_set: str,
    protocol: str,
    fold: str,
    model: str,
    seed: int,
    amin: float,
) -> dict:
    if not RESULTS.is_file():
        raise FileNotFoundError(f"Resultados de referência não encontrados: {RESULTS}")

    matches = []
    with RESULTS.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            if (
                record.get("task") == task
                and record.get("target") == target
                and record.get("feature_set") == feature_set
                and record.get("protocol") == protocol
                and record.get("fold") == fold
                and record.get("model") == model
                and record.get("seed") == seed
                and record.get("amin_ha") == (amin if task in (2, 3) else None)
                and not record.get("possible_duplicates_excluded", False)
                and record.get("imbalance_strategy", "default") == "default"
            ):
                matches.append(record)
    if len(matches) != 1:
        raise ValueError(
            f"Esperava um resultado de referência para tarefa={task}, "
            f"protocolo={protocol}, dobra={fold}, modelo={model}, seed={seed}; "
            f"encontrados {len(matches)}."
        )
    return matches[0]


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _confusion(frame: pd.DataFrame) -> dict:
    actual = frame["actual"].to_numpy(dtype=bool)
    predicted = frame["predicted"].to_numpy(dtype=bool)
    tp = int((actual & predicted).sum())
    fp = int((~actual & predicted).sum())
    fn = int((actual & ~predicted).sum())
    tn = int((~actual & ~predicted).sum())
    return {
        "rows": len(frame),
        "actual_positives": int(actual.sum()),
        "predicted_positives": int(predicted.sum()),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "false_positive_rate": _rate(fp, fp + tn),
        "false_negative_rate": _rate(fn, fn + tp),
        "precision": _rate(tp, tp + fp),
        "recall": _rate(tp, tp + fn),
    }


def _group_summary(frame: pd.DataFrame, column: str) -> list[dict]:
    summaries = []
    for value, group in frame.groupby(column, dropna=False, sort=True):
        summaries.append({"group": str(value), **_confusion(group)})
    return summaries


def _composition(errors: pd.DataFrame, categories: pd.Series) -> list[dict]:
    labels = categories.astype("string").fillna("unknown")
    counts = labels.value_counts(dropna=False).sort_index()
    total = len(errors)
    return [
        {"category": str(category), "count": int(count), "share": count / total}
        for category, count in counts.items()
    ]


def _error_composition(frame: pd.DataFrame, task: int, amin: float) -> dict:
    false_positives = frame.loc[frame["error_type"] == "false_positive"]
    false_negatives = frame.loc[frame["error_type"] == "false_negative"]
    if task == 1:
        fp_categories = pd.Series("predicted fire, none recorded", index=false_positives.index)
        fn_categories = pd.Series("missed recorded fire", index=false_negatives.index)
    elif task == 2:
        fp_categories = pd.Series(
            np.where(
                false_positives["target_only_n_incendios"] == 0,
                "no recorded fire",
                f"fire below {amin:g} ha",
            ),
            index=false_positives.index,
        )
        area = false_negatives["target_only_area_max_ha"]
        fn_categories = pd.cut(
            area,
            bins=[amin, 50, 100, 500, np.inf],
            right=False,
            labels=[f"{amin:g}-<50 ha", "50-<100 ha", "100-<500 ha", ">=500 ha"],
        )
    else:
        area_fp = false_positives["target_only_final_burned_area_ha"]
        fp_categories = pd.cut(
            area_fp,
            bins=[0, 1, 5, amin],
            right=False,
            labels=["<1 ha", "1-<5 ha", f"5-<{amin:g} ha"],
        )
        area_fn = false_negatives["target_only_final_burned_area_ha"]
        fn_categories = pd.cut(
            area_fn,
            bins=[amin, 50, 100, 500, np.inf],
            right=False,
            labels=[f"{amin:g}-<50 ha", "50-<100 ha", "100-<500 ha", ">=500 ha"],
        )
    return {
        "false_positives": _composition(false_positives, fp_categories),
        "false_negatives": _composition(false_negatives, fn_categories),
    }


def _error_frame(
    task: int,
    data: pd.DataFrame,
    y: pd.Series,
    test: np.ndarray,
    scores: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    frame = data.iloc[test].copy()
    frame["actual"] = y.iloc[test].to_numpy(dtype="int8")
    frame["predicted"] = (scores >= threshold).astype("int8")
    frame["error_type"] = np.select(
        [
            (frame["actual"] == 0) & (frame["predicted"] == 1),
            (frame["actual"] == 1) & (frame["predicted"] == 0),
        ],
        ["false_positive", "false_negative"],
        default="correct",
    )
    if task in (1, 2):
        frame["year"] = frame["date"].dt.year
        frame["month"] = frame["date"].dt.month
        frame["district"] = frame["cod_distrito"].astype(str)
        frame["municipality"] = frame["cod_concelho"].astype(str)
    else:
        frame["year"] = frame["data_hora_alerta"].dt.year
        frame["month"] = frame["data_hora_alerta"].dt.month
        frame["hour"] = frame["data_hora_alerta"].dt.hour
        frame["district"] = frame["feat_cod_distrito"].astype(str)
        frame["municipality"] = frame["feat_cod_concelho"].astype(str)
    return frame


def _run_analysis(
    task: int,
    model: str,
    protocol: str,
    seed: int,
    amin: float,
) -> list[dict]:
    target = _target(task, amin)
    feature_set = _feature_set_default(task)
    features = _features(task, feature_set)
    extra_columns = (
        ("target_only_n_incendios", "target_only_area_max_ha")
        if task in (1, 2)
        else ("target_only_final_burned_area_ha",)
    )
    data, y, _ = _load_data(
        task, target, features, extra_columns=extra_columns
    )
    folds = _splits(task, data, y, protocol, seed)
    output = []

    for fold_index, (fold_name, train, validation, test) in enumerate(folds):
        reference = _reference_record(
            task, target, feature_set, protocol, fold_name, model, seed, amin
        )
        metrics, selection, scores = _run_fold(
            model, features, seed, "default", seed + fold_index,
            data, y, train, validation, test,
        )
        expected_selection = reference["validation"]
        if selection["parameters"] != expected_selection["parameters"]:
            raise RuntimeError(
                f"{task}/{protocol}/{fold_name}/{model}: parâmetros selecionados "
                "diferem dos resultados registados."
            )
        if not np.isclose(
            selection["threshold_selected_on_validation"],
            expected_selection["threshold_selected_on_validation"],
            rtol=0,
            atol=1e-12,
        ):
            raise RuntimeError(
                f"{task}/{protocol}/{fold_name}/{model}: limiar de validação "
                "não reproduz o registo."
            )
        for metric in ("average_precision", "f1"):
            if not np.isclose(
                metrics[metric], reference["metrics"][metric], rtol=0, atol=1e-10
            ):
                raise RuntimeError(
                    f"{task}/{protocol}/{fold_name}/{model}: "
                    f"{metric} não reproduz o resultado registado."
                )

        frame = _error_frame(
            task, data, y, test, scores,
            selection["threshold_selected_on_validation"],
        )
        grouping = {
            "by_year": "year",
            "by_month": "month",
            "by_district": "district",
            "by_municipality": "municipality",
        }
        if task == 3:
            grouping["by_hour"] = "hour"
        output.append({
            "task": task,
            "target": target,
            "amin_ha": amin if task in (2, 3) else None,
            "model": model,
            "protocol": protocol,
            "fold": fold_name,
            "feature_set": feature_set,
            "features": features,
            "selection": selection,
            "reference_run_timestamp_utc": reference["run_timestamp_utc"],
            "test_period": reference["test_period"],
            "test_prevalence": reference["test_prevalence"],
            "metrics": metrics,
            "confusion": _confusion(frame),
            "errors_by": {
                name: _group_summary(frame, column)
                for name, column in grouping.items()
            },
            "error_composition": _error_composition(frame, task, amin),
        })
        print(
            f"T{task}/{protocol}/{fold_name}/{model}: "
            f"FP={metrics['fp']:,}, FN={metrics['fn']:,}, "
            f"F1={metrics['f1']:.4f}; referência reproduzida."
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="+", type=int, choices=(1, 2, 3), default=(1, 2, 3))
    parser.add_argument(
        "--models", nargs="+", choices=("logistic", "histgb"),
        default=("logistic", "histgb"),
    )
    parser.add_argument("--protocol", choices=PROTOCOLS, default="temporal")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    config = _config()
    seed = config["seed"] if args.seed is None else args.seed
    amin = float(config["amin_main"])
    if seed < 0:
        raise SystemExit("--seed tem de ser não negativo.")

    runs = []
    for task in args.tasks:
        for model in args.models:
            runs.extend(_run_analysis(task, model, args.protocol, seed, amin))

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_version": "ICNF-SGIF-2001-2025; CAOP2025 when required",
        "seed": seed,
        "protocol": args.protocol,
        "test_period": ["2021-01-01", "2025-12-31"] if args.protocol in (
            "temporal", "spatiotemporal"
        ) else None,
        "test_error_characterizations": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Relatório E9 escrito em {args.output}")


if __name__ == "__main__":
    main()
