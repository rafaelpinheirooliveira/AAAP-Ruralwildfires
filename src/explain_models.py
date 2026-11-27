"""Compute temporal-test permutation importance and partial dependence.

The model is reconstructed from the validation-selected parameters recorded by
run_experiments.py. The test set is used only for post-hoc explanations.
"""
from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.inspection import partial_dependence, permutation_importance
from sklearn.metrics import average_precision_score

from run_experiments import (
    PROTOCOLS,
    RESULTS,
    _best_f1_threshold,
    _config,
    _feature_set_default,
    _features,
    _load_data,
    _metrics,
    _pipeline,
    _scores,
    _splits,
    _target,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = RESULTS.parent / "e10_explainability.json"
FIGURES = RESULTS.parent / "figures"
IMPORTANCE_SAMPLE_SIZE = 100_000
PDP_SAMPLE_SIZE = 20_000
IMPORTANCE_REPEATS = 3
PDP_FEATURE_COUNT = 3


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


def _importance_sample(
    y: pd.Series, sample_size: int, seed: int
) -> np.ndarray:
    if len(y) <= sample_size:
        return np.arange(len(y))

    labels = y.to_numpy()
    positive = np.flatnonzero(labels == 1)
    negative = np.flatnonzero(labels == 0)
    rng = np.random.default_rng(seed)
    positive_count = min(
        len(positive), max(1, int(round(sample_size * len(positive) / len(y))))
    )
    negative_count = min(len(negative), sample_size - positive_count)
    selected = np.concatenate((
        rng.choice(positive, size=positive_count, replace=False),
        rng.choice(negative, size=negative_count, replace=False),
    ))
    return rng.permutation(selected)


def _plot_explanations(
    task: int,
    model: str,
    protocol: str,
    importances: list[dict],
    dependence: list[dict],
) -> str:
    figure_path = FIGURES / f"e10_task{task}_{model}_{protocol}.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(
        1 + len(dependence), 1,
        figsize=(10, 3.2 * (1 + len(dependence))),
        squeeze=False,
    )
    importance_axis = axes[0, 0]
    ordered = sorted(importances, key=lambda row: row["mean_ap_drop"])
    importance_axis.barh(
        [row["feature"] for row in ordered],
        [row["mean_ap_drop"] for row in ordered],
        xerr=[row["std_ap_drop"] for row in ordered],
        color="#4c78a8",
    )
    importance_axis.axvline(0, color="black", linewidth=0.8)
    importance_axis.set_xlabel("Queda média de AP após permutação")
    importance_axis.set_title("Importância por permutação (barras: desvio-padrão)")

    for axis, curve in zip(axes[1:, 0], dependence):
        axis.plot(curve["grid_values"], curve["average_probability"], color="#f58518")
        axis.set_xlabel(curve["feature"])
        axis.set_ylabel("Probabilidade média prevista")
        axis.set_title(f"Dependência parcial: {curve['feature']}")
    figure.suptitle(f"Tarefa {task} | {model} | protocolo {protocol}")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)
    return figure_path.relative_to(ROOT).as_posix()


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
    data, y, _ = _load_data(task, target, features)
    folds = _splits(task, data, y, protocol, seed)
    output = []

    for fold_index, (fold_name, train, validation, test) in enumerate(folds):
        reference = _reference_record(
            task, target, feature_set, protocol, fold_name, model, seed, amin
        )
        parameters = reference["validation"]["parameters"]
        if parameters.get("C", 1.0) != 1.0 or parameters.get("max_iter", 100) != 100:
            raise ValueError(
                f"{task}/{protocol}/{fold_name}/{model}: parâmetros não suportados."
            )
        estimator = _pipeline(
            model,
            seed,
            parameters.get("class_weight"),
            parameters.get("max_leaf_nodes", 31),
        )
        estimator.fit(data.iloc[train][features], y.iloc[train])
        validation_scores = _scores(estimator, data.iloc[validation][features])
        threshold = _best_f1_threshold(y.iloc[validation], validation_scores)
        if not np.isclose(
            threshold,
            reference["validation"]["threshold_selected_on_validation"],
            rtol=0,
            atol=1e-12,
        ):
            raise RuntimeError(
                f"{task}/{protocol}/{fold_name}/{model}: limiar de validação "
                "não reproduz o registo."
            )

        test = np.asarray(test)
        x_test = data.iloc[test][features]
        y_test = y.iloc[test]
        test_scores = _scores(estimator, x_test)
        metrics = _metrics(y_test, test_scores, threshold)
        for metric in ("average_precision", "f1"):
            if not np.isclose(
                metrics[metric], reference["metrics"][metric], rtol=0, atol=1e-10
            ):
                raise RuntimeError(
                    f"{task}/{protocol}/{fold_name}/{model}: "
                    f"{metric} não reproduz o resultado registado."
                )

        sample_rows = _importance_sample(
            y_test, IMPORTANCE_SAMPLE_SIZE, seed + task + fold_index
        )
        x_importance = x_test.iloc[sample_rows]
        y_importance = y_test.iloc[sample_rows]
        baseline_sample_ap = float(
            average_precision_score(
                y_importance, _scores(estimator, x_importance)
            )
        )
        importance_result = permutation_importance(
            estimator,
            x_importance,
            y_importance,
            scoring="average_precision",
            n_repeats=IMPORTANCE_REPEATS,
            random_state=seed + task + fold_index,
            n_jobs=1,
        )
        importances = [
            {
                "feature": feature,
                "mean_ap_drop": float(importance_result.importances_mean[index]),
                "std_ap_drop": float(importance_result.importances_std[index]),
                "repeats_ap_drop": [
                    float(value)
                    for value in importance_result.importances[index]
                ],
            }
            for index, feature in enumerate(features)
        ]
        top_features = [
            item["feature"]
            for item in sorted(
                importances, key=lambda row: row["mean_ap_drop"], reverse=True
            )[:PDP_FEATURE_COUNT]
        ]

        rng = np.random.default_rng(seed + 1000 + task + fold_index)
        pdp_rows = (
            np.arange(len(x_test))
            if len(x_test) <= PDP_SAMPLE_SIZE
            else rng.choice(len(x_test), size=PDP_SAMPLE_SIZE, replace=False)
        )
        x_pdp = x_test.iloc[pdp_rows].astype("float64")
        dependence = []
        for feature in top_features:
            result = partial_dependence(
                estimator,
                x_pdp,
                features=[feature],
                kind="average",
                grid_resolution=20,
                percentiles=(0.05, 0.95),
                response_method="predict_proba",
            )
            dependence.append({
                "feature": feature,
                "grid_values": [
                    float(value) for value in result["grid_values"][0]
                ],
                "average_probability": [
                    float(value) for value in result["average"][0]
                ],
                "sample_rows": len(x_pdp),
            })

        figure = _plot_explanations(
            task, model, protocol, importances, dependence
        )
        output.append({
            "task": task,
            "target": target,
            "amin_ha": amin if task in (2, 3) else None,
            "model": model,
            "protocol": protocol,
            "fold": fold_name,
            "feature_set": feature_set,
            "features": features,
            "selected_parameters": parameters,
            "threshold_selected_on_validation": threshold,
            "reference_run_timestamp_utc": reference["run_timestamp_utc"],
            "test_period": reference["test_period"],
            "test_rows": len(test),
            "test_positives": int(y_test.sum()),
            "test_average_precision": metrics["average_precision"],
            "test_f1": metrics["f1"],
            "importance_sample": {
                "rows": len(sample_rows),
                "positives": int(y_importance.sum()),
                "prevalence": float(y_importance.mean()),
                "baseline_average_precision": baseline_sample_ap,
                "permutation_repeats": IMPORTANCE_REPEATS,
            },
            "permutation_importance": importances,
            "partial_dependence": dependence,
            "figure": figure,
        })
        print(
            f"T{task}/{protocol}/{fold_name}/{model}: "
            f"AP teste={metrics['average_precision']:.4f}; "
            f"parâmetros e limiar reproduzidos."
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
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "seed": seed,
        "protocol": args.protocol,
        "importance_sample_size": IMPORTANCE_SAMPLE_SIZE,
        "importance_repeats": IMPORTANCE_REPEATS,
        "pdp_sample_size": PDP_SAMPLE_SIZE,
        "test_explanations": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Relatório E10 escrito em {args.output}")


if __name__ == "__main__":
    main()
