"""Train and evaluate a temporal model for next-election abstention."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


TARGET_YEAR = 2024
FEATURES = [
    "participation_rate",
    "abstention_rate",
    "non_specified_rate",
    "average_age",
    "under_30_share",
    "age_60_plus_share",
    "sex_0_share",
    "sex_1_share",
    "sex_2_share",
    "del_available_rate",
    "log_ln",
    "participation_change",
    "abstention_change",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def prepare_dataset(path: Path) -> tuple[pd.DataFrame, list[str]]:
    data = pd.read_csv(path, low_memory=False)
    if data.empty:
        raise ValueError(f"Dataset vacío: {path}")
    scope_keys = ["EDOCVE", "MPIOCVE"]
    if "SECCION" in data.columns:
        scope_keys += ["SECCION", "TIPOSEC"]
    data = data.sort_values(scope_keys + ["AELEC"]).copy()
    grouped = data.groupby(scope_keys, dropna=False, sort=False)
    data["previous_participation"] = grouped["participation_rate"].shift(1)
    data["previous_abstention"] = grouped["abstention_rate"].shift(1)
    data["participation_change"] = (
        data["participation_rate"] - data["previous_participation"]
    ).fillna(0)
    data["abstention_change"] = (
        data["abstention_rate"] - data["previous_abstention"]
    ).fillna(0)
    data["target_abstention"] = grouped["abstention_rate"].shift(-1)
    data["target_year"] = grouped["AELEC"].shift(-1)
    data["log_ln"] = np.log1p(data["LN"].clip(lower=0))
    data = data.dropna(subset=["target_abstention", "target_year"]).copy()
    data["target_year"] = data["target_year"].astype(int)
    return data, scope_keys


def metrics(y_true: pd.Series, prediction: np.ndarray) -> dict[str, float]:
    return {
        "mae": round(float(mean_absolute_error(y_true, prediction)), 6),
        "rmse": round(float(mean_squared_error(y_true, prediction) ** 0.5), 6),
        "r2": round(float(r2_score(y_true, prediction)), 6),
    }


def fit_gradient_boosting(x_train: pd.DataFrame, y_train: pd.Series) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=250,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=42,
    )
    model.fit(x_train, y_train)
    return model


def rolling_validation(data: pd.DataFrame, years: list[int]) -> dict[str, object]:
    results = {}
    for year in years:
        train = data[data["target_year"] < year]
        test = data[data["target_year"] == year]
        if train.empty or test.empty:
            continue
        x_train = train[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
        x_test = test[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
        model = fit_gradient_boosting(x_train, train["target_abstention"])
        prediction = model.predict(x_test).clip(0, 1)
        results[str(year)] = {
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "model": metrics(test["target_abstention"], prediction),
            "persistence_baseline": metrics(
                test["target_abstention"], test["abstention_rate"].to_numpy()
            ),
        }
    return results


def train_scope(input_path: Path, output_root: Path, scope: str) -> dict[str, object]:
    data, scope_keys = prepare_dataset(input_path)
    train = data[data["target_year"] < TARGET_YEAR].copy()
    test = data[data["target_year"] == TARGET_YEAR].copy()
    if train.empty or test.empty:
        raise ValueError(f"No hay train/test temporal suficiente para {scope}")

    x_train = train[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    x_test = test[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y_train = train["target_abstention"]
    y_test = test["target_abstention"]

    baseline_prediction = test["abstention_rate"].to_numpy()
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    ridge.fit(x_train, y_train)
    ridge_prediction = ridge.predict(x_test).clip(0, 1)

    model = fit_gradient_boosting(x_train, y_train)
    prediction = model.predict(x_test).clip(0, 1)

    importance_sample = min(10_000, len(x_test))
    importance = permutation_importance(
        model,
        x_test.iloc[:importance_sample],
        y_test.iloc[:importance_sample],
        n_repeats=3,
        random_state=42,
        scoring="neg_mean_absolute_error",
    )
    feature_importance = [
        {
            "feature": feature,
            "importance": round(float(value), 6),
        }
        for feature, value in sorted(
            zip(FEATURES, importance.importances_mean),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    predictions = test[scope_keys + ["target_year", "target_abstention"]].copy()
    predictions = predictions.rename(columns={"target_abstention": "actual_abstention"})
    predictions["baseline_abstention"] = baseline_prediction
    predictions["ridge_abstention"] = ridge_prediction
    predictions["predicted_abstention"] = prediction
    predictions["prediction_error"] = (
        predictions["predicted_abstention"] - predictions["actual_abstention"]
    )
    predictions["predicted_risk_level"] = pd.cut(
        predictions["predicted_abstention"],
        bins=[-np.inf, 0.399999, 0.599999, np.inf],
        labels=["bajo", "medio", "alto"],
    ).astype(str)

    output_root.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_root / f"ccpc_{scope}_predictions_2024.csv", index=False)
    summary = {
        "scope": scope,
        "target_year": TARGET_YEAR,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_target_years": sorted(train["target_year"].unique().tolist()),
        "models": {
            "persistence_baseline": metrics(y_test, baseline_prediction),
            "ridge": metrics(y_test, ridge_prediction),
            "hist_gradient_boosting": metrics(y_test, prediction),
        },
        "rolling_validation": rolling_validation(data, [2018, 2021, 2024]),
        "feature_importance": feature_importance,
    }
    (output_root / f"ccpc_{scope}_model_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "analytical")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "models")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for scope in ("section", "municipality"):
        summary = train_scope(
            args.input_root / f"ccpc_{scope}_year.csv",
            args.output_root,
            scope,
        )
        print(
            f"{scope}: MAE baseline={summary['models']['persistence_baseline']['mae']:.4f}, "
            f"model={summary['models']['hist_gradient_boosting']['mae']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
