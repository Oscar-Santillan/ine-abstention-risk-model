"""Construye un ?ndice territorial interpretable de riesgo de abstenci?n."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


LATEST_YEAR = 2024
MIN_YEARS_FOR_TREND = 3
DIMENSION_WEIGHTS = {
    "abstencion": 1 / 3,
    "tendencia": 1 / 3,
    "inestabilidad": 1 / 3,
}
LEVEL_BINS = [-np.inf, 33.333333, 66.666667, np.inf]
LEVEL_LABELS = ["bajo", "medio", "alto"]


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def clavesTerritoriales(data: pd.DataFrame) -> list[str]:
    keys = ["EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM"]
    if "SECCION" in data.columns:
        keys += ["SECCION", "TIPOSEC"]
    return keys


def calcularTendencia(group: pd.DataFrame) -> float:
    observed = group.dropna(subset=["AELEC", "tasa_participacion"])
    if len(observed) < MIN_YEARS_FOR_TREND:
        return np.nan
    return float(np.polyfit(observed["AELEC"], observed["tasa_participacion"], 1)[0])


def calcularPercentil(series: pd.Series) -> pd.Series:
    """Return a 0-100 rank percentile, preserving missing values."""

    count = series.notna().sum()
    if count <= 1:
        return series.where(series.notna(), np.nan)
    ranks = series.rank(method="average")
    return ranks.sub(1).div(count - 1).mul(100)


def explicarRiesgo(row: pd.Series) -> str:
    """Explain a zone's indiceRiesgo level using only signals that are actually available.

    ``puntaje_abstencion`` always rests on the latest observed election, so it is
    reported even when the historical series is short.  Trend and volatility, on
    the other hand, need at least three elections to be meaningful, so they are
    only reported when ``historico_confiable`` is true.
    """

    reasons = []
    reliable = bool(row["historico_confiable"])
    if row["puntaje_abstencion"] >= 66.666667:
        reasons.append("abstención reciente elevada")
    if reliable:
        if row["puntaje_tendencia"] >= 66.666667:
            reasons.append("tendencia descendente de participación")
        if row["puntaje_inestabilidad"] >= 66.666667:
            reasons.append("participación inestable")
    else:
        reasons.append("tendencia y volatilidad no disponibles por histórico insuficiente")
    if not reasons:
        reasons.append("señales históricas relativamente moderadas")
    return "; ".join(reasons)


def construirIndice(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, low_memory=False)
    if data.empty:
        raise ValueError(f"Dataset vacío: {path}")
    keys = clavesTerritoriales(data)
    required = keys + [
        "AELEC",
        "tasa_participacion",
        "tasa_abstencion",
        "tasa_no_especificado",
        "LN",
        "edad_promedio",
        "prop_menores_30",
        "prop_mayores_60",
    ]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {', '.join(missing)}")

    data = data.sort_values(keys + ["AELEC"]).copy()
    trend = (
        data.groupby(keys, dropna=False, sort=False)
        .apply(
            lambda group: pd.Series(
                {
                    "anos_observados": group["AELEC"].nunique(),
                    "pendiente_participacion": calcularTendencia(group),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    latest = data.loc[data["AELEC"] == LATEST_YEAR, keys + [
        "LN",
        "tasa_participacion",
        "tasa_abstencion",
        "tasa_no_especificado",
        "edad_promedio",
        "prop_menores_30",
        "prop_mayores_60",
        "volatilidad_participacion_3",
    ]].rename(
        columns={
            "LN": "ln_reciente",
            "tasa_participacion": "participacion_reciente",
            "tasa_abstencion": "abstencion_reciente",
            "tasa_no_especificado": "no_especificado_reciente",
            "edad_promedio": "edad_promedio_reciente",
            "prop_menores_30": "prop_menores_30_reciente",
            "prop_mayores_60": "prop_mayores_60_reciente",
            "volatilidad_participacion_3": "volatilidad_participacion_reciente",
        }
    )
    result = trend.merge(latest, on=keys, how="inner", validate="one_to_one")
    result["participacion_en_descenso"] = -result["pendiente_participacion"]
    result["volatilidad_participacion_reciente"] = (
        result["volatilidad_participacion_reciente"].fillna(0)
    )
    result["historico_confiable"] = result["anos_observados"] >= MIN_YEARS_FOR_TREND

    result["puntaje_abstencion"] = calcularPercentil(result["abstencion_reciente"])
    result["puntaje_tendencia"] = 100 - calcularPercentil(result["pendiente_participacion"])
    result.loc[~result["historico_confiable"], "puntaje_tendencia"] = np.nan
    # Volatility needs the same minimum history as trend: with one or two
    # elections a rolling std is 0 by construction, which would falsely signal
    # stability instead of an unmeasurable series.
    volatility = result["volatilidad_participacion_reciente"].where(
        result["historico_confiable"]
    )
    result["puntaje_inestabilidad"] = calcularPercentil(volatility)
    dimensions = result[
        ["puntaje_abstencion", "puntaje_tendencia", "puntaje_inestabilidad"]
    ]
    available_weights = dimensions.notna().mul(
        pd.Series(
            {
                "puntaje_abstencion": DIMENSION_WEIGHTS["abstencion"],
                "puntaje_tendencia": DIMENSION_WEIGHTS["tendencia"],
                "puntaje_inestabilidad": DIMENSION_WEIGHTS["inestabilidad"],
            }
        ),
        axis="columns",
    )
    result["indiceRiesgo_score"] = (
        dimensions.mul(available_weights).sum(axis=1)
        .div(available_weights.sum(axis=1))
        .where(result["historico_confiable"])
        .round(2)
    )
    result["indiceRiesgo_level"] = pd.cut(
        result["indiceRiesgo_score"],
        bins=LEVEL_BINS,
        labels=LEVEL_LABELS,
    ).astype("string")
    result.loc[~result["historico_confiable"], "indiceRiesgo_level"] = "sin_historico"
    result["indiceRiesgo_reason"] = result.apply(explicarRiesgo, axis=1)
    return result.sort_values(["indiceRiesgo_score"] + keys, ascending=[False] + [True] * len(keys))


def escribirAlcance(input_path: Path, output_path: Path, scope: str) -> dict[str, object]:
    result = construirIndice(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {
        "scope": scope,
        "input": str(input_path),
        "output": str(output_path),
        "rows": int(len(result)),
        "latest_year": LATEST_YEAR,
        "indiceRiesgo_levels": {
            level: int((result["indiceRiesgo_level"] == level).sum())
            for level in LEVEL_LABELS + ["sin_historico"]
        },
        "historico_confiable_rows": int(result["historico_confiable"].sum()),
        "non_specified_summary": {
            "median_2024": float(result["no_especificado_reciente"].median()),
            "p90_2024": float(result["no_especificado_reciente"].quantile(0.90)),
            "max_2024": float(result["no_especificado_reciente"].max()),
        },
    }


def interpretarArgumentos() -> argparse.Namespace:
    root = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "variables")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "indiceRiesgo")
    return parser.parse_args()


def main() -> int:
    args = interpretarArgumentos()
    report = {
        "project_area": "indiceRiesgo_index",
        "step": "interpretable_indiceRiesgo_index",
        "latest_year": LATEST_YEAR,
        "dimensions": {
            "abstencion": "Percentil de abstención reciente",
            "tendencia": "Percentil de disminución histórica de participación",
            "inestabilidad": "Percentil de volatilidad de participación en los últimos tres ejercicios",
        },
        "weights": DIMENSION_WEIGHTS,
        "weights_note": (
            "Pesos iguales como configuración neutral inicial; deben someterse a sensibilidad "
            "y validación institucional antes de usarse para asignar recursos."
        ),
        "limitations": [
            "La dimensión de tendencia usa la pendiente completa: valores positivos "
            "representan participación creciente y reciben una puntuación de riesgo baja.",
            "Las zonas con menos de tres años observados quedan como sin_historico y "
            "no reciben un indiceRiesgo_score, en lugar de imputar una tendencia.",
            "non_specified se conserva como indicador de calidad de registro, pero no "
            "se incorpora al riesgo de abstención.",
        ],
        "scopes": [],
    }
    for scope in ("section", "municipality"):
        report["scopes"].append(
            escribirAlcance(
                args.input_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}Variables.csv",
                args.output_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}IndiceRiesgo.csv",
                scope,
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "manifiestoIndiceRiesgo.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in report["scopes"]:
        print(f"{item['scope']}: {item['rows']:,} zonas clasificadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
