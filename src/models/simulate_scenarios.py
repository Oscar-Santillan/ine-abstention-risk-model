"""Simulate no-intervention and hypothetical intervention scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_UPLIFT = 0.05
HIGH_RISK_SCORE = 70.0
HIGH_PREDICTED_ABSTENTION = 0.40
SENSITIVITY_UPLIFTS = (0.02, 0.05, 0.10)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _keys(data: pd.DataFrame) -> list[str]:
    keys = ["EDOCVE", "MPIOCVE"]
    if "SECCION" in data.columns:
        keys += ["SECCION", "TIPOSEC"]
    return keys


def _risk_level(rate: pd.Series) -> pd.Series:
    return pd.cut(
        rate,
        bins=[-np.inf, 0.399999, 0.599999, np.inf],
        labels=["bajo", "medio", "alto"],
    ).astype(str)


def load_scope(prediction_path: Path, risk_path: Path) -> tuple[pd.DataFrame, list[str]]:
    predictions = pd.read_csv(prediction_path, low_memory=False)
    risk = pd.read_csv(risk_path, low_memory=False)
    keys = _keys(predictions)
    risk_columns = keys + [
        "EDONOM",
        "MPIONOM",
        "latest_ln",
        "risk_score",
        "risk_level",
        "latest_abstention",
        "participation_slope",
        "participation_volatility",
    ]
    risk_columns = [column for column in risk_columns if column in risk.columns]
    data = predictions.merge(risk[risk_columns], on=keys, how="inner", validate="one_to_one")
    if data.empty:
        raise ValueError(f"No se pudieron unir predicciones y riesgo para {prediction_path}")
    data["latest_ln"] = pd.to_numeric(data["latest_ln"], errors="coerce").fillna(0)
    data["predicted_abstention"] = pd.to_numeric(
        data["predicted_abstention"], errors="coerce"
    ).clip(0, 1)
    data["priority_zone"] = (
        (data["risk_score"] >= HIGH_RISK_SCORE)
        | (data["predicted_abstention"] >= HIGH_PREDICTED_ABSTENTION)
    )
    return data, keys


def simulate(data: pd.DataFrame, uplift: float) -> pd.DataFrame:
    if not 0 <= uplift <= 1:
        raise ValueError("uplift debe estar entre 0 y 1")
    result = data.copy()
    result["base_abstention"] = result["predicted_abstention"]
    result["base_participation"] = 1 - result["base_abstention"]
    result["intervention_uplift"] = np.where(result["priority_zone"], uplift, 0)
    result["intervention_participation"] = (
        result["base_participation"] + result["intervention_uplift"]
    ).clip(0, 1)
    result["intervention_abstention"] = 1 - result["intervention_participation"]
    result["abstention_reduction"] = (
        result["base_abstention"] - result["intervention_abstention"]
    ).clip(lower=0)
    result["base_expected_abstainers"] = result["base_abstention"] * result["latest_ln"]
    result["intervention_expected_abstainers"] = (
        result["intervention_abstention"] * result["latest_ln"]
    )
    result["expected_abstainers_avoided"] = (
        result["base_expected_abstainers"]
        - result["intervention_expected_abstainers"]
    ).clip(lower=0)
    result["base_risk_level"] = _risk_level(result["base_abstention"])
    result["intervention_risk_level"] = _risk_level(result["intervention_abstention"])
    return result


def summary(data: pd.DataFrame, uplift: float, scope: str) -> dict[str, object]:
    targeted = data["priority_zone"]
    return {
        "scope": scope,
        "assumptions": {
            "base": "Predicted abstention from the temporally validated model.",
            "intervention": (
                f"An absolute {uplift:.1%} participation uplift in priority zones only; "
                "this is a planning simulation, not a causal estimate."
            ),
            "priority_rule": (
                f"risk_score >= {HIGH_RISK_SCORE:.0f} OR predicted abstention >= "
                f"{HIGH_PREDICTED_ABSTENTION:.0%}"
            ),
        },
        "zones": int(len(data)),
        "priority_zones": int(targeted.sum()),
        "priority_share": round(float(targeted.mean()), 6),
        "base_weighted_abstention": round(
            float(data["base_expected_abstainers"].sum() / data["latest_ln"].sum()), 6
        ),
        "intervention_weighted_abstention": round(
            float(data["intervention_expected_abstainers"].sum() / data["latest_ln"].sum()),
            6,
        ),
        "expected_abstainers_avoided": round(float(data["expected_abstainers_avoided"].sum()), 2),
        "priority_expected_abstainers_avoided": round(
            float(data.loc[targeted, "expected_abstainers_avoided"].sum()), 2
        ),
        "risk_level_counts_base": data["base_risk_level"].value_counts().to_dict(),
        "risk_level_counts_intervention": data["intervention_risk_level"].value_counts().to_dict(),
    }


def run_scope(prediction_path: Path, risk_path: Path, output_root: Path, scope: str) -> None:
    data, keys = load_scope(prediction_path, risk_path)
    scenario = simulate(data, DEFAULT_UPLIFT)
    output_root.mkdir(parents=True, exist_ok=True)
    scenario.sort_values(
        ["priority_zone", "base_abstention", "risk_score"],
        ascending=[False, False, False],
    ).to_csv(output_root / f"ccpc_{scope}_scenarios.csv", index=False)

    sensitivity = []
    for uplift in SENSITIVITY_UPLIFTS:
        sensitivity_data = simulate(data, uplift)
        sensitivity.append(summary(sensitivity_data, uplift, scope))
    report = {
        "scope": scope,
        "keys": keys,
        "default_uplift": DEFAULT_UPLIFT,
        "default_summary": summary(scenario, DEFAULT_UPLIFT, scope),
        "sensitivity": sensitivity,
    }
    (output_root / f"ccpc_{scope}_scenarios.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"{'Secciones' if scope == 'section' else 'Municipios'}: {len(scenario):,} zonas, "
        f"{int(scenario['priority_zone'].sum()):,} prioritarias, "
        f"{scenario['expected_abstainers_avoided'].sum():,.0f} "
        "abstenciones evitadas simuladas"
    )


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", type=Path, default=root / "outputs" / "models")
    parser.add_argument("--risk-root", type=Path, default=root / "outputs" / "risk")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "scenarios")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for scope in ("section", "municipality"):
        run_scope(
            args.models_root / f"ccpc_{scope}_predictions_2024.csv",
            args.risk_root / f"ccpc_{scope}_risk.csv",
            args.output_root,
            scope,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
