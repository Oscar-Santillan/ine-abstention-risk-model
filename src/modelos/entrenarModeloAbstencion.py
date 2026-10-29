"""Entrena modelos temporales para predecir la abstenci?n de la siguiente elecci?n."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline


TARGET = "target_abstention"
TEST_TARGET_YEAR = 2024
RANDOM_STATE = 42
FEATURE_COLUMNS = [
    "tasa_participacion",
    "tasa_abstencion",
    "tasa_no_especificado",
    "edad_promedio",
    "tasa_del_disponible",
    "prop_sex_0",
    "prop_sex_1",
    "prop_sex_2",
    "prop_menores_30",
    "prop_30_59",
    "prop_mayores_60",
    "ln_log",
    "participacion_previa",
    "abstencion_previa",
    "cambio_participacion",
    "cambio_abstencion",
    "media_participacion_3",
    "media_abstencion_3",
    "volatilidad_participacion_3",
    "min_participacion_3",
    "max_participacion_3",
]


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)),
    }


def entrenarAlcance(
    input_path: Path, prediction_path: Path, importance_path: Path, scope: str
) -> dict[str, object]:
    data = pd.read_csv(input_path, low_memory=False)
    required = FEATURE_COLUMNS + [TARGET, "target_year", "AELEC"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {input_path}: {', '.join(missing)}")

    labeled = data.loc[data[TARGET].notna() & data["target_year"].notna()].copy()
    train = labeled.loc[labeled["target_year"] < TEST_TARGET_YEAR].copy()
    test = labeled.loc[labeled["target_year"] == TEST_TARGET_YEAR].copy()
    if train.empty or test.empty:
        raise ValueError(f"No hay partición temporal válida para {scope}")

    x_train = train[FEATURE_COLUMNS]
    x_test = test[FEATURE_COLUMNS]
    y_train = train[TARGET]
    y_test = test[TARGET]

    baseline_prediction = test["abstencion_previa"].fillna(
        y_train.mean()
    )
    baseline_metrics = metrics(y_test, baseline_prediction)

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=300,
                    min_samples_leaf=3,
                    max_features=0.8,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    model_metrics = metrics(y_test, prediction)

    output = test.copy()
    output["baseline_prediction"] = baseline_prediction.to_numpy()
    output["model_prediction"] = prediction
    output["absolute_error"] = (output[TARGET] - output["model_prediction"]).abs()
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(prediction_path, index=False)

    importances = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "importance": model.named_steps["model"].feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance_path.parent.mkdir(parents=True, exist_ok=True)
    importances.to_csv(importance_path, index=False)

    return {
        "scope": scope,
        "input": str(input_path),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_target_years": sorted(train["target_year"].astype(int).unique().tolist()),
        "test_target_year": TEST_TARGET_YEAR,
        "target": TARGET,
        "baseline": {
            "name": "abstencion_previa",
            **baseline_metrics,
        },
        "random_forest": model_metrics,
        "best_model": (
            "random_forest"
            if model_metrics["mae"] <= baseline_metrics["mae"]
            else "baseline"
        ),
        "top_variables": importances.head(10).to_dict(orient="records"),
    }


def interpretarArgumentos() -> argparse.Namespace:
    root = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "variables")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "modelos")
    return parser.parse_args()


def main() -> int:
    args = interpretarArgumentos()
    report = {
        "project_area": "temporal_abstention_model",
        "step": "temporal_abstention_model",
        "method": "RandomForestRegressor",
        "split": {
            "training": "target_year < 2024",
            "testing": "target_year == 2024",
        },
        "feature_columns": FEATURE_COLUMNS,
        "scopes": [],
    }
    for scope in ("section", "municipality"):
        report["scopes"].append(
            entrenarAlcance(
                args.input_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}Variables.csv",
                args.output_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}Predicciones.csv",
                args.output_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}ImportanciaVariables.csv",
                scope,
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "manifiestoModelo.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in report["scopes"]:
        print(
            f"{item['scope']}: MAE RF={item['random_forest']['mae']:.4f}, "
            f"baseline={item['baseline']['mae']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
