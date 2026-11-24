"""Train and evaluate the wildfire classifiers with leakage-safe data splits.

Examples:
    python src/run_experiments.py --task 1 --protocol temporal
    python src/run_experiments.py --task 2 --protocol spatiotemporal --max-folds 1
    python src/run_experiments.py --task 3 --protocol random
    python src/run_experiments.py --task 1 --protocol temporal --dry-run
"""
from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import yaml
from pyproj import Transformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from attach_cems_features import CEMS_VARIABLES
from build_territory_day_dataset import FEATURES_AT_2359
from integrate_cems import load_municipalities

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/config.yaml"
TERRITORY = ROOT / "data/processed/territory_day.parquet"
OCCURRENCES = ROOT / "data/processed/occurrences.parquet"
CEMS_FEATURES = ROOT / "data/processed/cems_features.parquet"
RESULTS = ROOT / "results/experiments.jsonl"

DAILY_CALENDAR = ["feat_mes", "feat_dia_do_ano", "feat_dia_da_semana"]
ALERT_CALENDAR = ["feat_mes", "feat_dia_do_ano", "feat_dia_da_semana", "feat_hora"]
CEMS_LAG1 = [f"{feature}_lag1" for feature in CEMS_VARIABLES]
PROTOCOLS = ("random", "temporal", "spatial", "spatiotemporal")
MODELS = ("prior", "history", "logistic", "histgb")


def _config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _target(task: int, amin: float) -> str:
    if task == 1:
        return "y_fire"
    return f"y_sig_amin{amin:g}"


def _features(task: int, feature_set: str) -> list[str]:
    if task in (1, 2):
        options = {
            "calendar": DAILY_CALENDAR,
            "history": FEATURES_AT_2359,
            "history-location": FEATURES_AT_2359 + ["feat_centroid_latitude", "feat_centroid_longitude"],
            "history-cems": FEATURES_AT_2359 + CEMS_LAG1,
            "history-location-cems": (
                FEATURES_AT_2359 + ["feat_centroid_latitude", "feat_centroid_longitude"] + CEMS_LAG1
            ),
        }
    else:
        options = {
            "temporal": ALERT_CALENDAR,
            "temporal-location": ALERT_CALENDAR + ["feat_latitude", "feat_longitude"],
            "temporal-location-cems": ALERT_CALENDAR + ["feat_latitude", "feat_longitude"] + CEMS_LAG1,
        }
    if feature_set not in options:
        valid = ", ".join(options)
        raise ValueError(f"Conjunto de features inválido para a tarefa {task}; opções: {valid}")
    return list(options[feature_set])


def _municipality_centroids() -> pd.DataFrame:
    codes, geometries = load_municipalities()
    to_wgs84 = Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True)
    rows = []
    for code, geometry in zip(codes, geometries):
        centroid = geometry.centroid
        longitude, latitude = to_wgs84.transform(centroid.x, centroid.y)
        rows.append((code, latitude, longitude))
    return pd.DataFrame(
        rows, columns=["cod_concelho", "feat_centroid_latitude", "feat_centroid_longitude"]
    )


def _load_data(
    task: int,
    target: str,
    features: list[str],
    exclude_possible_duplicates: bool = False,
) -> tuple[pd.DataFrame, pd.Series, int]:
    if exclude_possible_duplicates and task != 3:
        raise ValueError("A exclusão de possíveis duplicados só se aplica à Tarefa 3.")

    excluded_duplicate_rows = 0
    derived_features = set(CEMS_LAG1) | {
        "feat_centroid_latitude", "feat_centroid_longitude",
    }
    source_features = [feature for feature in features if feature not in derived_features]
    if task in (1, 2):
        metadata = ["date", "cod_concelho", "cod_distrito"]
        needed = list(dict.fromkeys(metadata + source_features + [target]))
        data = pd.read_parquet(TERRITORY, columns=needed)
        data["date"] = pd.to_datetime(data["date"])
        data["cod_concelho"] = data["cod_concelho"].astype(str).str.zfill(4)
        data["cod_distrito"] = data["cod_distrito"].astype(str).str.zfill(2)
        if "feat_centroid_latitude" in features:
            data = data.merge(_municipality_centroids(), on="cod_concelho", how="left", validate="many_to_one")
    else:
        metadata = ["data_hora_alerta", "ano", "feat_cod_distrito", "feat_cod_concelho"]
        if exclude_possible_duplicates:
            metadata.append("flag_possivel_duplicado")
        needed = list(dict.fromkeys(metadata + source_features + [target]))
        data = pd.read_parquet(OCCURRENCES, columns=needed)
        data["data_hora_alerta"] = pd.to_datetime(data["data_hora_alerta"])
        data["ano"] = data["data_hora_alerta"].dt.year
        data["feat_cod_distrito"] = data["feat_cod_distrito"].astype(str).str.zfill(2)
        data["feat_cod_concelho"] = data["feat_cod_concelho"].astype(str).str.zfill(4)
        if exclude_possible_duplicates:
            duplicate_mask = data["flag_possivel_duplicado"].fillna(False).astype(bool)
            excluded_duplicate_rows = int(duplicate_mask.sum())
            data = (
                data.loc[~duplicate_mask]
                .drop(columns="flag_possivel_duplicado")
                .reset_index(drop=True)
            )

    if any(feature in CEMS_LAG1 for feature in features):
        if not CEMS_FEATURES.is_file():
            raise FileNotFoundError(
                f"Features CEMS não encontradas: {CEMS_FEATURES}. "
                "Conclua o descarregamento, a agregação e src/attach_cems_features.py."
            )
        date_key = "date" if task in (1, 2) else "data_hora_alerta"
        if task == 3:
            data["_cems_date"] = data[date_key].dt.normalize()
            date_key = "_cems_date"
        cems = pd.read_parquet(CEMS_FEATURES, columns=["date", "cod_concelho", *CEMS_LAG1])
        cems["date"] = pd.to_datetime(cems["date"])
        if task == 1 or task == 2:
            data = data.merge(
                cems, left_on=["date", "cod_concelho"], right_on=["date", "cod_concelho"],
                how="left", validate="many_to_one",
            )
        else:
            data = data.merge(
                cems, left_on=[date_key, "feat_cod_concelho"], right_on=["date", "cod_concelho"],
                how="left", validate="many_to_one",
            ).drop(columns=["date", "cod_concelho", "_cems_date"])

    if data[target].isna().any():
        raise ValueError(f"O alvo {target} contém valores em falta.")
    if not set(data[target].unique()) <= {0, 1}:
        raise ValueError(f"O alvo {target} não é binário.")
    if not set(features) <= set(data.columns):
        raise ValueError("Há features em falta após carregar e juntar os datasets.")
    return data, data[target].astype("int8"), excluded_duplicate_rows


def _coordinates_and_groups(task: int, data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    if task in (1, 2):
        years = data["date"].dt.year.to_numpy()
        districts = data["cod_distrito"].to_numpy()
    else:
        years = data["ano"].to_numpy()
        districts = data["feat_cod_distrito"].to_numpy()
    return years, districts


def _district_fold_ids(districts: np.ndarray) -> tuple[np.ndarray, dict[str, int]]:
    unique = sorted(set(districts))
    mapping = {district: index % 6 for index, district in enumerate(unique)}
    return np.array([mapping[district] for district in districts]), mapping


def _random_splits(
    task: int, data: pd.DataFrame, y: pd.Series, seed: int
) -> list[tuple[str, np.ndarray, np.ndarray, np.ndarray]]:
    if task == 3:
        group_keys = pd.MultiIndex.from_arrays(
            [data["feat_cod_concelho"], data["data_hora_alerta"].dt.normalize()]
        )
        groups, _ = pd.factorize(group_keys, sort=False)
        rng = np.random.default_rng(seed)
        group_order = rng.permutation(groups.max() + 1)
        group_folds = np.empty(len(group_order), dtype="int8")
        group_folds[group_order] = np.arange(len(group_order)) % 5
        fold_ids = group_folds[groups]
        outer_splits = [
            (np.flatnonzero(fold_ids != fold), np.flatnonzero(fold_ids == fold))
            for fold in range(5)
        ]
    else:
        splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        outer_splits = splitter.split(data, y)

    folds = []
    for fold, (outer_train, test) in enumerate(outer_splits):
        if task == 3:
            inner_groups, inner_codes = np.unique(groups[outer_train], return_inverse=True)
            rng = np.random.default_rng(seed + fold)
            order = rng.permutation(len(inner_groups))
            validation_group_mask = np.zeros(len(inner_groups), dtype=bool)
            validation_group_mask[order[:max(1, int(round(len(order) * 0.2)))]] = True
            validation_mask = validation_group_mask[inner_codes]
            train = outer_train[~validation_mask]
            validation = outer_train[validation_mask]
            if y.iloc[train].nunique() < 2 or y.iloc[validation].nunique() < 2:
                raise ValueError("A divisão agrupada deixou um conjunto sem ambas as classes.")
        else:
            rng = np.random.default_rng(seed + fold)
            shuffled = rng.permutation(outer_train)
            validation_size = max(1, int(round(len(shuffled) * 0.2)))
            validation, train = shuffled[:validation_size], shuffled[validation_size:]
            if y.iloc[train].nunique() < 2 or y.iloc[validation].nunique() < 2:
                raise ValueError("A divisão aleatória deixou um conjunto sem ambas as classes.")
        folds.append((f"fold-{fold}", train, validation, test))
    return folds


def _splits(
    task: int, data: pd.DataFrame, y: pd.Series, protocol: str, seed: int
) -> list[tuple[str, np.ndarray, np.ndarray, np.ndarray]]:
    years, districts = _coordinates_and_groups(task, data)
    all_rows = np.arange(len(data))
    if protocol == "temporal":
        train = all_rows[years <= 2017]
        validation = all_rows[(years >= 2018) & (years <= 2020)]
        test = all_rows[(years >= 2021) & (years <= 2025)]
        folds = [("temporal-2021-2025", train, validation, test)]
    elif protocol in ("spatial", "spatiotemporal"):
        district_folds, _ = _district_fold_ids(districts)
        folds = []
        for test_fold in range(6):
            validation_fold = (test_fold + 1) % 6
            test_mask = district_folds == test_fold
            validation_mask = district_folds == validation_fold
            train_mask = ~test_mask & ~validation_mask
            if protocol == "spatiotemporal":
                train_mask &= years <= 2017
                validation_mask &= (years >= 2018) & (years <= 2020)
                test_mask &= (years >= 2021) & (years <= 2025)
            train = all_rows[train_mask]
            validation = all_rows[validation_mask]
            test = all_rows[test_mask]
            folds.append((f"district-fold-{test_fold}", train, validation, test))
    else:
        return _random_splits(task, data, y, seed)

    for name, train, validation, test in folds:
        if not len(train) or not len(validation) or not len(test):
            raise ValueError(f"{name}: divisão vazia no protocolo {protocol}.")
        for label, rows in (("treino", train), ("validação", validation), ("teste", test)):
            if y.iloc[rows].nunique() < 2:
                raise ValueError(f"{name}: o conjunto de {label} não tem ambas as classes.")
    return folds


def _pipeline(model: str, seed: int, class_weight: str | None = None, leaves: int = 31):
    if model == "logistic":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            LogisticRegression(
                C=1.0, class_weight=class_weight, max_iter=300, random_state=seed,
                solver="lbfgs",
            ),
        )
    if model == "histgb":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            HistGradientBoostingClassifier(
                class_weight=class_weight,
                early_stopping=True,
                learning_rate=0.1,
                max_iter=100,
                max_leaf_nodes=leaves,
                random_state=seed,
            ),
        )
    if model == "prior":
        return DummyClassifier(strategy="prior")
    raise ValueError(f"Modelo desconhecido: {model}")


def _candidates(model: str, seed: int) -> list[tuple[object, dict]]:
    if model == "logistic":
        return [
            (_pipeline(model, seed, weight), {"class_weight": weight, "C": 1.0})
            for weight in (None, "balanced")
        ]
    if model == "histgb":
        return [
            (_pipeline(model, seed, "balanced", leaves), {
                "class_weight": "balanced", "max_leaf_nodes": leaves, "max_iter": 100,
            })
            for leaves in (15, 31)
        ]
    if model == "prior":
        return [(_pipeline(model, seed), {"strategy": "prior"})]
    return []


def _best_f1_threshold(y: pd.Series, scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y, scores)
    if len(thresholds) == 0:
        return 0.5
    f1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-12)
    return float(thresholds[int(np.nanargmax(f1))])


def _metrics(
    y: pd.Series, scores: np.ndarray, threshold: float, probability_scores: bool = True
) -> dict:
    predicted = scores >= threshold
    return {
        "average_precision": float(average_precision_score(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
        "brier": float(brier_score_loss(y, scores)) if probability_scores else None,
        "tn": int(((y == 0) & ~predicted).sum()),
        "fp": int(((y == 0) & predicted).sum()),
        "fn": int(((y == 1) & ~predicted).sum()),
        "tp": int(((y == 1) & predicted).sum()),
    }


def _scores(estimator, x: pd.DataFrame) -> np.ndarray:
    probabilities = estimator.predict_proba(x)
    classes = list(estimator.classes_)
    positive = classes.index(1)
    return probabilities[:, positive]


def _run_fold(
    model: str,
    features: list[str],
    seed: int,
    data: pd.DataFrame,
    y: pd.Series,
    train: np.ndarray,
    validation: np.ndarray,
    test: np.ndarray,
) -> tuple[dict, dict]:
    x_train = data.iloc[train][features]
    y_train = y.iloc[train]
    x_validation = data.iloc[validation][features]
    y_validation = y.iloc[validation]
    x_test = data.iloc[test][features]
    y_test = y.iloc[test]

    best = None
    if model == "history":
        if "feat_n_incendios_7d" not in features:
            raise ValueError("O baseline de histórico requer feat_n_incendios_7d.")
        validation_scores = x_validation["feat_n_incendios_7d"].to_numpy(dtype="float64")
        best = (None, {"rule": "feat_n_incendios_7d"}, validation_scores)
    else:
        best_ap = -np.inf
        for estimator, parameters in _candidates(model, seed):
            estimator.fit(x_train, y_train)
            candidate_scores = _scores(estimator, x_validation)
            score = average_precision_score(y_validation, candidate_scores)
            if score > best_ap:
                best_ap = score
                best = (estimator, parameters, candidate_scores)
        if best is None:
            raise ValueError(f"Sem candidatos para o modelo {model}.")
    validation_scores = best[2]
    threshold = (
        0.5 if model == "prior"
        else _best_f1_threshold(y_validation, validation_scores)
    )

    estimator, parameters = best[:2]
    if model == "history":
        test_scores = x_test["feat_n_incendios_7d"].to_numpy(dtype="float64")
    else:
        test_scores = _scores(estimator, x_test)
    metrics = _metrics(y_test, test_scores, threshold, probability_scores=model != "history")
    return metrics, {
        "parameters": parameters,
        "threshold_selected_on_validation": threshold,
        "validation_average_precision": float(average_precision_score(y_validation, validation_scores)),
    }


def _feature_set_default(task: int) -> str:
    return "history" if task in (1, 2) else "temporal-location"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--protocol", choices=PROTOCOLS, required=True)
    parser.add_argument("--amin", type=float, default=10)
    parser.add_argument("--seed", type=int, help="seed (por omissão, configs/config.yaml)")
    parser.add_argument("--feature-set")
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument(
        "--exclude-possible-duplicates", action="store_true",
        help="sensibilidade da Tarefa 3 sem os registos assinalados como possíveis duplicados",
    )
    parser.add_argument("--max-folds", type=int, help="limita folds para testes rápidos")
    parser.add_argument(
        "--resume", action="store_true",
        help="salta as dobras já registadas no ficheiro de saída",
    )
    parser.add_argument("--dry-run", action="store_true", help="valida dados e divisões sem treinar")
    parser.add_argument("--output", type=Path, default=RESULTS)
    args = parser.parse_args()

    config = _config()
    seed = config["seed"] if args.seed is None else args.seed
    if seed < 0:
        raise SystemExit("--seed tem de ser não negativo.")
    if args.amin not in {config["amin_main"], *config["amin_sensitivity"]}:
        raise SystemExit(f"Amin tem de ser um dos valores configurados: "
                         f"{config['amin_sensitivity']} ou {config['amin_main']}.")
    feature_set = args.feature_set or _feature_set_default(args.task)
    if args.exclude_possible_duplicates and args.task != 3:
        raise SystemExit("--exclude-possible-duplicates só se aplica à Tarefa 3.")
    features = _features(args.task, feature_set)
    target = _target(args.task, args.amin)
    data, y, excluded_duplicate_rows = _load_data(
        args.task, target, features, args.exclude_possible_duplicates
    )
    if args.exclude_possible_duplicates:
        print(f"Excluídos {excluded_duplicate_rows:,} registos assinalados como possíveis duplicados.")
    folds = _splits(args.task, data, y, args.protocol, seed)
    if args.max_folds is not None:
        if args.max_folds < 1:
            raise SystemExit("--max-folds tem de ser positivo.")
        folds = folds[:args.max_folds]

    for name, train, validation, test in folds:
        print(
            f"{name}: treino={len(train):,} ({int(y.iloc[train].sum()):,} positivos), "
            f"validação={len(validation):,} ({int(y.iloc[validation].sum()):,}), "
            f"teste={len(test):,} ({int(y.iloc[test].sum()):,})"
        )
    if args.dry_run:
        return

    completed = set()
    if args.resume and args.output.is_file():
        with args.output.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (
                    record.get("task") == args.task
                    and record.get("target") == target
                    and record.get("protocol") == args.protocol
                    and record.get("feature_set") == feature_set
                    and record.get("seed") == seed
                    and record.get("possible_duplicates_excluded", False)
                    == args.exclude_possible_duplicates
                ):
                    completed.add((record.get("fold"), record.get("model")))

    for fold_name, train, validation, test in folds:
        for model in args.models:
            if (fold_name, model) in completed:
                print(f"  {model}: {fold_name} já registada; ignorada")
                continue
            if model == "history" and not any(
                feature in features for feature in ("feat_n_incendios_7d",)
            ):
                if args.task == 3:
                    raise SystemExit("O baseline history só se aplica às Tarefas 1 e 2.")
                raise SystemExit("O baseline history requer o conjunto de features history.")
            metrics, selection = _run_fold(
                model, features, seed, data, y, train, validation, test
            )
            record = {
                "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "dataset_version": "ICNF-SGIF-2001-2025; CAOP2025 when required",
                "python_version": platform.python_version(),
                "scikit_learn_version": sklearn.__version__,
                "task": args.task,
                "unit": "municipality-day" if args.task in (1, 2) else "occurrence",
                "target": target,
                "amin_ha": args.amin if args.task in (2, 3) else None,
                "prediction_moment": "23:59 d-1" if args.task in (1, 2) else "DataHoraAlerta",
                "protocol": args.protocol,
                "fold": fold_name,
                "feature_set": feature_set,
                "features": features,
                "possible_duplicates_excluded": args.exclude_possible_duplicates,
                "excluded_possible_duplicate_rows": excluded_duplicate_rows,
                "model": model,
                "seed": seed,
                "train_rows": len(train),
                "train_positives": int(y.iloc[train].sum()),
                "validation_rows": len(validation),
                "validation_positives": int(y.iloc[validation].sum()),
                "test_rows": len(test),
                "test_positives": int(y.iloc[test].sum()),
                "test_prevalence": float(y.iloc[test].mean()),
                "test_period": [
                    str(data.iloc[test]["date"].min().date()),
                    str(data.iloc[test]["date"].max().date()),
                ] if args.task in (1, 2) else [
                    str(data.iloc[test]["data_hora_alerta"].min()),
                    str(data.iloc[test]["data_hora_alerta"].max()),
                ],
                "test_district_codes": sorted(
                    data.iloc[test]["cod_distrito"].astype(str).unique().tolist()
                ) if args.task in (1, 2) else sorted(
                    data.iloc[test]["feat_cod_distrito"].astype(str).unique().tolist()
                ),
                "validation": selection,
                "metrics": metrics,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(
                f"  {model}: PR-AUC={metrics['average_precision']:.4f}, "
                f"ROC-AUC={metrics['roc_auc']:.4f}, F1={metrics['f1']:.4f}"
            )


if __name__ == "__main__":
    main()
