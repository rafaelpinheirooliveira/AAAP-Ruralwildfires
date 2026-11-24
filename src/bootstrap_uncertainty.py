"""Estimate monthly block-bootstrap confidence intervals for test average precision.

The script reconstructs each selected seed-42 model on its original training
fold and resamples whole test months, preserving within-month dependence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import average_precision_score

from run_experiments import (
    _load_data,
    _pipeline,
    _scores,
    _splits,
)

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "results/experiments.jsonl"
OUTPUT = ROOT / "results/uncertainty.jsonl"


def _bootstrap_seed(record: dict, base_seed: int) -> int:
    key = "|".join(
        str(value)
        for value in (
            base_seed,
            record["task"],
            record["protocol"],
            record["fold"],
            record["model"],
            record["seed"],
        )
    )
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _block_bootstrap_ap(
    y: np.ndarray,
    scores: np.ndarray,
    block_ids: np.ndarray,
    replicates: int,
    seed: int,
    confidence_level: float,
) -> tuple[float, float, int]:
    unique_blocks, row_blocks = np.unique(block_ids, return_inverse=True)
    if len(unique_blocks) < 2:
        raise ValueError("O teste tem menos de dois blocos mensais.")

    order = np.argsort(scores, kind="mergesort")[::-1]
    sorted_scores = scores[order]
    sorted_y = y[order].astype("float64", copy=False)
    sorted_blocks = row_blocks[order]
    threshold_indices = np.r_[
        np.flatnonzero(np.diff(sorted_scores)),
        len(sorted_scores) - 1,
    ]

    rng = np.random.default_rng(seed)
    block_count = len(unique_blocks)
    probabilities = np.full(block_count, 1.0 / block_count)
    samples = np.empty(replicates, dtype="float64")
    valid = 0

    for _ in range(replicates):
        multiplicities = rng.multinomial(block_count, probabilities)
        weights = multiplicities[sorted_blocks]
        weighted_positives = float(np.dot(sorted_y, weights))
        weighted_total = float(weights.sum())
        if weighted_positives == 0 or weighted_positives == weighted_total:
            continue

        true_positives = np.cumsum(sorted_y * weights)[threshold_indices]
        predicted_positives = np.cumsum(weights)[threshold_indices]
        precision = np.divide(
            true_positives,
            predicted_positives,
            out=np.zeros_like(true_positives),
            where=predicted_positives > 0,
        )
        recall_increments = np.diff(np.r_[0.0, true_positives]) / weighted_positives
        samples[valid] = np.sum(recall_increments * precision)
        valid += 1

    minimum_valid = max(100, int(replicates * 0.9))
    if valid < minimum_valid:
        raise ValueError(
            f"Só {valid}/{replicates} réplicas bootstrap válidas; "
            f"mínimo exigido: {minimum_valid}."
        )

    tail = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(samples[:valid], [tail, 1.0 - tail])
    return float(lower), float(upper), valid


def _selected_estimator(record: dict):
    parameters = record["validation"]["parameters"]
    model = record["model"]
    seed = int(record["seed"])
    if model == "logistic":
        return _pipeline(model, seed, parameters["class_weight"])
    if model == "histgb":
        return _pipeline(
            model,
            seed,
            parameters["class_weight"],
            int(parameters["max_leaf_nodes"]),
        )
    raise ValueError(f"Modelo não suportado para bootstrap: {model}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=int, choices=(1, 2, 3))
    parser.add_argument(
        "--protocol",
        choices=("random", "temporal", "spatial", "spatiotemporal"),
    )
    parser.add_argument("--seed", type=int, default=42, help="seed da experiência a analisar")
    parser.add_argument("--replicates", type=int, default=1000)
    parser.add_argument("--bootstrap-seed", type=int, default=2026)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if args.replicates < 100:
        raise SystemExit("--replicates tem de ser pelo menos 100.")
    if args.seed < 0 or args.bootstrap_seed < 0:
        raise SystemExit("As seeds têm de ser não negativas.")
    if not 0.0 < args.confidence_level < 1.0:
        raise SystemExit("--confidence-level tem de estar entre 0 e 1.")
    if not EXPERIMENTS.is_file():
        raise SystemExit(f"Registo de experiências não encontrado: {EXPERIMENTS}")

    with EXPERIMENTS.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]

    selected = [
        record for record in records
        if record.get("model") in {"logistic", "histgb"}
        and record.get("seed") == args.seed
        and not record.get("possible_duplicates_excluded", False)
    ]
    if args.task is not None:
        selected = [
            record for record in selected
            if record.get("task") == args.task
        ]
    if args.protocol is not None:
        selected = [
            record for record in selected
            if record.get("protocol") == args.protocol
        ]
    selected = [
        record for record in selected
        if not any(str(feature).endswith("_lag1") for feature in record.get("features", []))
    ]
    if not selected:
        raise SystemExit("Não há experiências elegíveis para esta seleção.")

    existing = set()
    if args.resume and args.output.is_file():
        with args.output.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                result = json.loads(line)
                existing.add(
                    (
                        result["task"],
                        result["target"],
                        result["protocol"],
                        result["fold"],
                        result["model"],
                        result["seed"],
                        result["bootstrap_seed"],
                        result["bootstrap_replicates"],
                        result["confidence_level"],
                    )
                )

    data_cache: dict[tuple, tuple[pd.DataFrame, pd.Series]] = {}
    split_cache: dict[tuple, dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]] = {}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    for record in selected:
        task = int(record["task"])
        target = str(record["target"])
        features = tuple(record["features"])
        experiment_seed = int(record["seed"])
        data_key = (task, target, features)
        if data_key not in data_cache:
            data, y, excluded = _load_data(task, target, list(features))
            if excluded:
                raise ValueError("A experiência principal não pode excluir duplicados.")
            data_cache[data_key] = (data, y)
        data, y = data_cache[data_key]

        split_key = (
            task, target, features, record["protocol"], experiment_seed,
        )
        if split_key not in split_cache:
            split_cache[split_key] = {
                name: (train, validation, test)
                for name, train, validation, test in _splits(
                    task, data, y, record["protocol"], experiment_seed
                )
            }
        try:
            train, _, test = split_cache[split_key][record["fold"]]
        except KeyError as error:
            raise ValueError(
                f"Dobra não encontrada ao reconstruir a divisão: "
                f"{task}/{record['protocol']}/{record['fold']}."
            ) from error

        key = (
            task,
            target,
            record["protocol"],
            record["fold"],
            record["model"],
            experiment_seed,
            _bootstrap_seed(record, args.bootstrap_seed),
            args.replicates,
            args.confidence_level,
        )
        if key in existing:
            print(
                f"  task={task} {record['protocol']} {record['fold']} "
                f"{record['model']}: já registado; ignorado"
            )
            continue

        if len(test) != record["test_rows"]:
            raise ValueError(
                f"Tamanho de teste divergente em {task}/{record['protocol']}/"
                f"{record['fold']}: {len(test)} != {record['test_rows']}."
            )
        if int(y.iloc[test].sum()) != record["test_positives"]:
            raise ValueError(
                f"Positivos de teste divergentes em {task}/{record['protocol']}/"
                f"{record['fold']}."
            )
        x_train = data.iloc[train][list(features)]
        y_train = y.iloc[train]
        x_test = data.iloc[test][list(features)]
        y_test = y.iloc[test].to_numpy(dtype="int8")

        estimator = _selected_estimator(record)
        estimator.fit(x_train, y_train)
        scores = _scores(estimator, x_test)
        point_estimate = float(average_precision_score(y_test, scores))
        if not np.isclose(
            point_estimate, record["metrics"]["average_precision"], atol=1e-8
        ):
            raise ValueError(
                f"AP reconstruída divergente em {task}/{record['protocol']}/"
                f"{record['fold']}/{record['model']}: {point_estimate} != "
                f"{record['metrics']['average_precision']}."
            )

        time_column = "date" if task in (1, 2) else "data_hora_alerta"
        months = (
            pd.to_datetime(data.iloc[test][time_column])
            .dt.to_period("M")
            .astype(str)
            .to_numpy()
        )
        bootstrap_seed = key[6]
        lower, upper, valid = _block_bootstrap_ap(
            y_test,
            scores,
            months,
            args.replicates,
            bootstrap_seed,
            args.confidence_level,
        )

        result = {
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_version": record["dataset_version"],
            "task": task,
            "target": target,
            "amin_ha": record["amin_ha"],
            "protocol": record["protocol"],
            "fold": record["fold"],
            "feature_set": record["feature_set"],
            "model": record["model"],
            "seed": experiment_seed,
            "test_rows": len(test),
            "test_positives": int(y_test.sum()),
            "test_prevalence": float(y_test.mean()),
            "threshold_selected_on_validation": record["validation"][
                "threshold_selected_on_validation"
            ],
            "average_precision": point_estimate,
            "confidence_level": args.confidence_level,
            "block_unit": "calendar_month",
            "bootstrap_replicates": args.replicates,
            "bootstrap_valid_replicates": valid,
            "bootstrap_seed": bootstrap_seed,
            "average_precision_ci_lower": lower,
            "average_precision_ci_upper": upper,
            "scikit_learn_version": sklearn.__version__,
        }
        with args.output.open("a", encoding="utf-8") as file:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")
        existing.add(key)
        print(
            f"task={task} {record['protocol']} {record['fold']} {record['model']}: "
            f"AP={point_estimate:.4f}, 95% CI [{lower:.4f}, {upper:.4f}] "
            f"({valid}/{args.replicates} réplicas)"
        )


if __name__ == "__main__":
    main()
