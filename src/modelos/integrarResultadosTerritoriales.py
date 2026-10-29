"""Integra el ?ndice interpretable y las predicciones por territorio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


BASE_KEYS = ["EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM"]
SECTION_KEYS = BASE_KEYS + ["SECCION", "TIPOSEC"]
RISK_COLUMNS = [
    "years_observed",
    "participation_slope",
    "latest_ln",
    "latest_participation",
    "latest_abstention",
    "latest_non_specified",
    "latest_average_age",
    "latest_under_30_share",
    "latest_age_60_plus_share",
    "latest_participation_volatility_3",
    "declining_participation",
    "trend_reliable",
    "abstencion_score",
    "tendencia_score",
    "inestabilidad_score",
    "indiceRiesgo_score",
    "indiceRiesgo_level",
    "indiceRiesgo_reason",
]
PREDICTION_COLUMNS = [
    "target_year",
    "previous_abstention",
    "baseline_prediction",
    "model_prediction",
    "absolute_error",
]


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def integrarAlcance(
    indiceRiesgo_path: Path,
    prediction_path: Path,
    output_path: Path,
    scope: str,
    selected_model: str,
) -> dict[str, object]:
    keys = SECTION_KEYS if scope == "section" else BASE_KEYS
    indiceRiesgo = pd.read_csv(indiceRiesgo_path, low_memory=False)
    predictions = pd.read_csv(prediction_path, low_memory=False)
    missing_indiceRiesgo = [column for column in keys + RISK_COLUMNS if column not in indiceRiesgo]
    missing_predictions = [
        column for column in keys + PREDICTION_COLUMNS if column not in predictions
    ]
    if missing_indiceRiesgo:
        raise ValueError(f"Faltan columnas de riesgo en {indiceRiesgo_path}: {missing_indiceRiesgo}")
    if missing_predictions:
        raise ValueError(
            f"Faltan columnas de predicción en {prediction_path}: {missing_predictions}"
        )

    indiceRiesgo = indiceRiesgo[keys + RISK_COLUMNS].copy()
    predictions = predictions.loc[
        predictions["target_year"].eq(2024), keys + PREDICTION_COLUMNS
    ].copy()
    if predictions.empty:
        raise ValueError(f"No hay predicciones para 2024 en {prediction_path}")
    if predictions.duplicated(keys).any():
        raise ValueError(f"Hay predicciones duplicadas por zona en {prediction_path}")
    if indiceRiesgo.duplicated(keys).any():
        raise ValueError(f"Hay riesgos duplicados por zona en {indiceRiesgo_path}")

    predictions = predictions.rename(
        columns={
            "target_year": "prediction_target_year",
            "previous_abstention": "model_previous_abstention",
            "baseline_prediction": "predicted_abstention_baseline",
            "model_prediction": "predicted_abstention_random_forest",
            "absolute_error": "random_forest_absolute_error",
        }
    )
    result = indiceRiesgo.merge(predictions, on=keys, how="left", validate="one_to_one")
    result["selected_prediction_model"] = selected_model
    result["predicted_abstention"] = result[
        f"predicted_abstention_{selected_model}"
    ]
    result["prediction_available"] = result["predicted_abstention"].notna()
    result["dashboard_status"] = result["indiceRiesgo_level"].replace(
        {"sin_historico": "sin_historico"}
    )
    result = result.sort_values(
        ["indiceRiesgo_score"] + keys,
        ascending=[False] + [True] * len(keys),
        na_position="last",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {
        "scope": scope,
        "input_indiceRiesgo": str(indiceRiesgo_path),
        "input_predictions": str(prediction_path),
        "output": str(output_path),
        "rows": int(len(result)),
        "prediction_rows": int(result["prediction_available"].sum()),
        "prediction_coverage": float(result["prediction_available"].mean()),
        "indiceRiesgo_rows_with_history": int(result["trend_reliable"].sum()),
        "indiceRiesgo_levels": result["indiceRiesgo_level"].value_counts(dropna=False).to_dict(),
        "selected_prediction_model": selected_model,
        "alignment_note": (
            "La predicción se enlaza por claves territoriales nominales y códigos. "
            "En secciones, la cobertura puede ser menor porque la numeración puede "
            "cambiar entre ejercicios electorales."
        ),
    }


def interpretarArgumentos() -> argparse.Namespace:
    root = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indiceRiesgo-root", type=Path, default=root / "outputs" / "indiceRiesgo")
    parser.add_argument("--model-root", type=Path, default=root / "outputs" / "modelos")
    parser.add_argument(
        "--output-root", type=Path, default=root / "outputs" / "resultadosIntegrados"
    )
    return parser.parse_args()


def main() -> int:
    args = interpretarArgumentos()
    report = {
        "project_area": "resultadosIntegrados_territorial_results",
        "step": "resultadosIntegrados_territorial_results",
        "description": (
            "Tabla maestra que combina el índice interpretable, la predicción "
            "temporal y el estado de confiabilidad por territorio."
        ),
        "prediction_target_year": 2024,
        "limitations": [
            "Las predicciones corresponden al objetivo 2024 y se enlazan con el "
            "territorio observado en 2024 mediante sus claves disponibles.",
            "La cobertura de predicción de secciones es parcial porque las secciones "
            "pueden renumerarse entre ejercicios; una ausencia no equivale a riesgo bajo.",
        ],
        "scopes": [],
    }
    for scope in ("section", "municipality"):
        report["scopes"].append(
            integrarAlcance(
                args.indiceRiesgo_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}IndiceRiesgo.csv",
                args.model_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}Predicciones.csv",
                args.output_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}ResultadosIntegrados.csv",
                scope,
                "random_forest" if scope == "section" else "baseline",
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "manifiestoIntegracion.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in report["scopes"]:
        print(f"{item['scope']}: {item['rows']:,} zonas integradas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
