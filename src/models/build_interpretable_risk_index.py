"""Build a transparent territorial abstention-risk index."""

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


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def territorial_keys(data: pd.DataFrame) -> list[str]:
    keys = ["EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM"]
    if "SECCION" in data.columns:
        keys += ["SECCION", "TIPOSEC"]
    return keys


def _trend(group: pd.DataFrame) -> float:
    observed = group.dropna(subset=["AELEC", "participation_rate"])
    if len(observed) < MIN_YEARS_FOR_TREND:
        return np.nan
    return float(np.polyfit(observed["AELEC"], observed["participation_rate"], 1)[0])


def _percentile(series: pd.Series) -> pd.Series:
    """Return a 0-100 rank percentile, preserving missing values."""

    count = series.notna().sum()
    if count <= 1:
        return series.where(series.notna(), np.nan)
    ranks = series.rank(method="average")
    return ranks.sub(1).div(count - 1).mul(100)


def _reason(row: pd.Series) -> str:
    """Explain a zone's risk level using only signals that are actually available.

    ``abstencion_score`` always rests on the latest observed election, so it is
    reported even when the historical series is short.  Trend and volatility, on
    the other hand, need at least three elections to be meaningful, so they are
    only reported when ``trend_reliable`` is true.
    """

    reasons = []
    reliable = bool(row["trend_reliable"])
    if row["abstencion_score"] >= 66.666667:
        reasons.append("abstención reciente elevada")
    if reliable:
        if row["tendencia_score"] >= 66.666667:
            reasons.append("tendencia descendente de participación")
        if row["inestabilidad_score"] >= 66.666667:
            reasons.append("participación inestable")
    else:
        reasons.append("tendencia y volatilidad no disponibles por histórico insuficiente")
    if not reasons:
        reasons.append("señales históricas relativamente moderadas")
    return "; ".join(reasons)


def build_index(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, low_memory=False)
    if data.empty:
        raise ValueError(f"Dataset vacío: {path}")
    keys = territorial_keys(data)
    required = keys + [
        "AELEC",
        "participation_rate",
        "abstention_rate",
        "non_specified_rate",
        "LN",
        "average_age",
        "under_30_share",
        "age_60_plus_share",
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
                    "years_observed": group["AELEC"].nunique(),
                    "participation_slope": _trend(group),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    latest = data.loc[data["AELEC"] == LATEST_YEAR, keys + [
        "LN",
        "participation_rate",
        "abstention_rate",
        "non_specified_rate",
        "average_age",
        "under_30_share",
        "age_60_plus_share",
        "participation_volatility_3",
    ]].rename(
        columns={
            "LN": "latest_ln",
            "participation_rate": "latest_participation",
            "abstention_rate": "latest_abstention",
            "non_specified_rate": "latest_non_specified",
            "average_age": "latest_average_age",
            "under_30_share": "latest_under_30_share",
            "age_60_plus_share": "latest_age_60_plus_share",
            "participation_volatility_3": "latest_participation_volatility_3",
        }
    )
    result = trend.merge(latest, on=keys, how="inner", validate="one_to_one")
    result["declining_participation"] = -result["participation_slope"]
    result["latest_participation_volatility_3"] = (
        result["latest_participation_volatility_3"].fillna(0)
    )
    result["trend_reliable"] = result["years_observed"] >= MIN_YEARS_FOR_TREND

    result["abstencion_score"] = _percentile(result["latest_abstention"])
    result["tendencia_score"] = 100 - _percentile(result["participation_slope"])
    result.loc[~result["trend_reliable"], "tendencia_score"] = np.nan
    # Volatility needs the same minimum history as trend: with one or two
    # elections a rolling std is 0 by construction, which would falsely signal
    # stability instead of an unmeasurable series.
    volatility = result["latest_participation_volatility_3"].where(
        result["trend_reliable"]
    )
    result["inestabilidad_score"] = _percentile(volatility)
    dimensions = result[
        ["abstencion_score", "tendencia_score", "inestabilidad_score"]
    ]
    available_weights = dimensions.notna().mul(
        pd.Series(
            {
                "abstencion_score": DIMENSION_WEIGHTS["abstencion"],
                "tendencia_score": DIMENSION_WEIGHTS["tendencia"],
                "inestabilidad_score": DIMENSION_WEIGHTS["inestabilidad"],
            }
        ),
        axis="columns",
    )
    result["risk_score"] = (
        dimensions.mul(available_weights).sum(axis=1)
        .div(available_weights.sum(axis=1))
        .where(result["trend_reliable"])
        .round(2)
    )
    result["risk_level"] = pd.cut(
        result["risk_score"],
        bins=LEVEL_BINS,
        labels=LEVEL_LABELS,
    ).astype("string")
    result.loc[~result["trend_reliable"], "risk_level"] = "sin_historico"
    result["risk_reason"] = result.apply(_reason, axis=1)
    return result.sort_values(["risk_score"] + keys, ascending=[False] + [True] * len(keys))


def write_scope(input_path: Path, output_path: Path, scope: str) -> dict[str, object]:
    result = build_index(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {
        "scope": scope,
        "input": str(input_path),
        "output": str(output_path),
        "rows": int(len(result)),
        "latest_year": LATEST_YEAR,
        "risk_levels": {
            level: int((result["risk_level"] == level).sum())
            for level in LEVEL_LABELS + ["sin_historico"]
        },
        "trend_reliable_rows": int(result["trend_reliable"].sum()),
        "non_specified_summary": {
            "median_2024": float(result["latest_non_specified"].median()),
            "p90_2024": float(result["latest_non_specified"].quantile(0.90)),
            "max_2024": float(result["latest_non_specified"].max()),
        },
    }


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "features")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "risk")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "project_area": "risk_index",
        "step": "interpretable_risk_index",
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
            "no reciben un risk_score, en lugar de imputar una tendencia.",
            "non_specified se conserva como indicador de calidad de registro, pero no "
            "se incorpora al riesgo de abstención.",
        ],
        "scopes": [],
    }
    for scope in ("section", "municipality"):
        report["scopes"].append(
            write_scope(
                args.input_root / f"ccpc_{scope}_features.csv",
                args.output_root / f"ccpc_{scope}_risk_index.csv",
                scope,
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "risk_index_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in report["scopes"]:
        print(f"{item['scope']}: {item['rows']:,} zonas clasificadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
