"""Build leakage-safe features for the Stage-II risk index and ML model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


YEARS = (2009, 2012, 2015, 2018, 2021, 2024)
BASE_COLUMNS = [
    "AELEC",
    "FELECCION",
    "EDOCVE",
    "EDONOM",
    "MPIOCVE",
    "MPIONOM",
    "LN",
    "SV",
    "NV",
    "NS",
    "participation_rate",
    "abstention_rate",
    "non_specified_rate",
    "average_age",
    "del_available_rate",
    "sex_0_share",
    "sex_1_share",
    "sex_2_share",
    "under_30_share",
    "age_30_59_share",
    "age_60_plus_share",
]
HISTORICAL_FEATURES = [
    "log_ln",
    "previous_participation",
    "previous_abstention",
    "participation_change",
    "abstention_change",
    "participation_mean_3",
    "abstention_mean_3",
    "participation_volatility_3",
    "participation_min_3",
    "participation_max_3",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def scope_keys(data: pd.DataFrame) -> list[str]:
    keys = ["EDOCVE", "MPIOCVE"]
    if "SECCION" in data.columns:
        keys += ["SECCION", "TIPOSEC"]
    return keys


def _validate_input(data: pd.DataFrame, path: Path) -> None:
    missing = [column for column in BASE_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {', '.join(missing)}")
    if data.empty:
        raise ValueError(f"Dataset vacío: {path}")


def build_features(data: pd.DataFrame) -> pd.DataFrame:
    """Create current, lagged and trailing features without future information."""

    data = data.copy()
    keys = scope_keys(data)
    data["AELEC"] = pd.to_numeric(data["AELEC"], errors="raise").astype(int)
    data = data.sort_values(keys + ["AELEC"]).reset_index(drop=True)
    grouped = data.groupby(keys, dropna=False, sort=False)

    data["log_ln"] = np.log1p(pd.to_numeric(data["LN"], errors="coerce").clip(lower=0))
    data["previous_participation"] = grouped["participation_rate"].shift(1)
    data["previous_abstention"] = grouped["abstention_rate"].shift(1)
    data["participation_change"] = (
        data["participation_rate"] - data["previous_participation"]
    )
    data["abstention_change"] = data["abstention_rate"] - data["previous_abstention"]

    history = grouped["participation_rate"].rolling(window=3, min_periods=1)
    data["participation_mean_3"] = history.mean().reset_index(level=keys, drop=True).to_numpy()
    data["participation_volatility_3"] = (
        history.std(ddof=0).reset_index(level=keys, drop=True).to_numpy()
    )
    data["participation_min_3"] = history.min().reset_index(level=keys, drop=True).to_numpy()
    data["participation_max_3"] = history.max().reset_index(level=keys, drop=True).to_numpy()
    abstention_history = grouped["abstention_rate"].rolling(window=3, min_periods=1)
    data["abstention_mean_3"] = (
        abstention_history.mean().reset_index(level=keys, drop=True).to_numpy()
    )

    data["target_abstention"] = grouped["abstention_rate"].shift(-1)
    data["target_year"] = grouped["AELEC"].shift(-1)
    data["has_next_observation"] = data["target_year"].notna()
    data["target_year"] = data["target_year"].astype("Int64")
    data["participation_change"] = data["participation_change"].fillna(0)
    data["abstention_change"] = data["abstention_change"].fillna(0)
    data["previous_participation"] = data["previous_participation"].fillna(
        data["participation_rate"]
    )
    data["previous_abstention"] = data["previous_abstention"].fillna(
        data["abstention_rate"]
    )
    data["participation_volatility_3"] = data["participation_volatility_3"].fillna(0)
    return data


def validate_features(data: pd.DataFrame) -> None:
    keys = scope_keys(data)
    if data.duplicated(keys + ["AELEC"]).any():
        raise ValueError("Hay claves territoriales-año duplicadas en las features")
    target_rows = data["has_next_observation"]
    if (data.loc[target_rows, "target_year"] <= data.loc[target_rows, "AELEC"]).any():
        raise ValueError("Se detectó un objetivo temporal que no es posterior al año actual")
    for column in HISTORICAL_FEATURES:
        if not pd.api.types.is_numeric_dtype(data[column]):
            raise TypeError(f"La feature {column} no es numérica")


def write_scope(input_path: Path, output_path: Path) -> dict[str, object]:
    data = pd.read_csv(input_path, low_memory=False)
    _validate_input(data, input_path)
    result = build_features(data)
    validate_features(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "rows": int(len(result)),
        "columns_added": HISTORICAL_FEATURES + ["target_abstention", "target_year"],
        "rows_with_next_observation": int(result["has_next_observation"].sum()),
    }


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "analytical")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "features")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {"stage": "Stage-II", "step": "feature_engineering", "scopes": []}
    for scope in ("section", "municipality"):
        report["scopes"].append(
            write_scope(
                args.input_root / f"ccpc_{scope}_year.csv",
                args.output_root / f"ccpc_{scope}_features.csv",
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "feature_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in report["scopes"]:
        print(f"{item['output']}: {item['rows']:,} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
