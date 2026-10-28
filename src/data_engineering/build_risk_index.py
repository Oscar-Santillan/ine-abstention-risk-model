"""Build an interpretable 0-100 abstention risk index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


LATEST_YEAR = 2024
MIN_YEARS_FOR_TREND = 3
WEIGHTS = {
    "recent_abstention": 0.45,
    "declining_trend": 0.35,
    "volatility": 0.15,
    "non_specified": 0.05,
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _slope(group: pd.DataFrame) -> float:
    if len(group) < MIN_YEARS_FOR_TREND:
        return np.nan
    x = group["AELEC"].to_numpy(dtype=float)
    y = group["participation_rate"].to_numpy(dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def build_index(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, low_memory=False)
    if data.empty:
        raise ValueError(f"Dataset vacío: {path}")
    keys = ["EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM"]
    if "SECCION" in data.columns:
        keys += ["SECCION", "TIPOSEC"]

    data = data.sort_values(keys + ["AELEC"])
    trend = (
        data.groupby(keys, dropna=False, sort=False)
        .apply(
            lambda group: pd.Series(
                {
                    "years_observed": group["AELEC"].nunique(),
                    "participation_slope": _slope(group),
                    "participation_volatility": group["participation_rate"].std(ddof=0),
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
        "del_available_rate",
    ]].rename(
        columns={
            "LN": "latest_ln",
            "participation_rate": "latest_participation",
            "abstention_rate": "latest_abstention",
            "non_specified_rate": "latest_non_specified",
            "average_age": "latest_average_age",
            "under_30_share": "latest_under_30_share",
            "age_60_plus_share": "latest_age_60_plus_share",
            "del_available_rate": "latest_del_available_rate",
        }
    )
    result = trend.merge(latest, on=keys, how="inner", validate="one_to_one")
    result["declining_trend"] = (-result["participation_slope"]).clip(lower=0).fillna(0)
    result["participation_volatility"] = result["participation_volatility"].fillna(0)
    result["years_observed"] = result["years_observed"].astype(int)

    components = {
        "recent_abstention": "latest_abstention",
        "declining_trend": "declining_trend",
        "volatility": "participation_volatility",
        "non_specified": "latest_non_specified",
    }
    for name, column in components.items():
        result[f"{name}_percentile"] = result[column].rank(method="average", pct=True) * 100
    result["risk_score"] = sum(
        WEIGHTS[name] * result[f"{name}_percentile"] for name in components
    )
    result["risk_score"] = result["risk_score"].round(2)
    result["risk_level"] = pd.cut(
        result["risk_score"],
        bins=[-np.inf, 39.999, 69.999, np.inf],
        labels=["bajo", "medio", "alto"],
    ).astype(str)
    result["trend_reliable"] = result["years_observed"] >= MIN_YEARS_FOR_TREND
    return result.sort_values(["risk_score"] + keys, ascending=[False] + [True] * len(keys))


def write_outputs(result: pd.DataFrame, output: Path, scope: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    summary = {
        "scope": scope,
        "latest_year": LATEST_YEAR,
        "minimum_years_for_trend": MIN_YEARS_FOR_TREND,
        "weights": WEIGHTS,
        "score_definition": (
            "Weighted percentile score: recent abstention 45%, declining participation "
            "trend 35%, historical volatility 15%, latest non-specified share 5%."
        ),
        "rows": int(len(result)),
        "risk_levels": {
            str(level): int((result["risk_level"] == level).sum())
            for level in ("bajo", "medio", "alto")
        },
        "trend_reliable_rows": int(result["trend_reliable"].sum()),
    }
    output.with_suffix(".json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "analytical")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "risk")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for scope in ("section", "municipality"):
        result = build_index(args.input_root / f"ccpc_{scope}_year.csv")
        write_outputs(result, args.output_root / f"ccpc_{scope}_risk.csv", scope)
        print(
            f"{'Secciones' if scope == 'section' else 'Municipios'}: "
            f"{len(result):,} zonas con riesgo calculado"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
