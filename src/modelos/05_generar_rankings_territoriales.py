"""Build transparent territorial rankings from integrated Stage-II results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


TOP_N = 100
RISK_LEVELS = ("alto", "medio", "bajo")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ranking_columns(scope: str) -> list[str]:
    columns = ["EDONOM", "MPIONOM"]
    if scope == "section":
        columns += ["SECCION", "TIPOSEC"]
    return columns


def build_scope_rankings(
    input_path: Path, output_root: Path, scope: str
) -> dict[str, object]:
    data = pd.read_csv(input_path, low_memory=False)
    required = ranking_columns(scope) + [
        "risk_score",
        "risk_level",
        "risk_reason",
        "trend_reliable",
        "predicted_abstention",
        "prediction_available",
        "latest_abstention",
    ]
    missing = [column for column in required if column not in data]
    if missing:
        raise ValueError(f"Faltan columnas en {input_path}: {missing}")

    data = data.copy()
    data["risk_rank"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    reliable = data["risk_score"].notna()
    data.loc[reliable, "risk_rank"] = (
        data.loc[reliable, "risk_score"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    data["prediction_rank"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    predicted = data["predicted_abstention"].notna()
    data.loc[predicted, "prediction_rank"] = (
        data.loc[predicted, "predicted_abstention"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

    prediction_high_threshold = data.loc[predicted, "predicted_abstention"].quantile(
        0.75
    )
    data["priority_signal"] = "seguimiento"
    data.loc[~data["trend_reliable"], "priority_signal"] = "sin_historico"
    data.loc[
        data["trend_reliable"] & data["risk_level"].eq("alto"), "priority_signal"
    ] = "riesgo_alto"
    data.loc[
        data["trend_reliable"]
        & data["predicted_abstention"].ge(prediction_high_threshold),
        "priority_signal",
    ] = "prediccion_alta"
    data.loc[
        data["trend_reliable"]
        & data["risk_level"].eq("alto")
        & data["predicted_abstention"].ge(prediction_high_threshold),
        "priority_signal",
    ] = "riesgo_alto_y_prediccion_alta"

    output_root.mkdir(parents=True, exist_ok=True)
    top_risk = data.loc[reliable].sort_values(
        ["risk_score"] + ranking_columns(scope),
        ascending=[False] + [True] * len(ranking_columns(scope)),
    ).head(TOP_N)
    top_prediction = data.loc[predicted].sort_values(
        ["predicted_abstention"] + ranking_columns(scope),
        ascending=[False] + [True] * len(ranking_columns(scope)),
    ).head(TOP_N)
    top_priority = data.loc[
        data["priority_signal"].eq("riesgo_alto_y_prediccion_alta")
    ].sort_values(
        ["risk_score", "predicted_abstention"] + ranking_columns(scope),
        ascending=[False, False] + [True] * len(ranking_columns(scope)),
    ).head(TOP_N)

    top_risk.to_csv(output_root / f"top_{scope}_by_risk.csv", index=False)
    top_prediction.to_csv(
        output_root / f"top_{scope}_by_predicted_abstention.csv", index=False
    )
    top_priority.to_csv(
        output_root / f"top_{scope}_priority_candidates.csv", index=False
    )

    state_summary = (
        data.groupby("EDONOM", dropna=False)
        .agg(
            zones=("EDONOM", "size"),
            reliable_zones=("trend_reliable", "sum"),
            high_risk_zones=("risk_level", lambda values: (values == "alto").sum()),
            predicted_zones=("prediction_available", "sum"),
            mean_risk_score=("risk_score", "mean"),
            mean_predicted_abstention=("predicted_abstention", "mean"),
        )
        .reset_index()
        .sort_values(["high_risk_zones", "mean_risk_score"], ascending=[False, False])
    )
    state_summary.to_csv(output_root / f"{scope}_state_summary.csv", index=False)

    return {
        "scope": scope,
        "input": str(input_path),
        "zones": int(len(data)),
        "reliable_zones": int(reliable.sum()),
        "prediction_available_zones": int(predicted.sum()),
        "prediction_high_threshold": float(prediction_high_threshold),
        "top_risk_rows": int(len(top_risk)),
        "top_prediction_rows": int(len(top_prediction)),
        "priority_candidate_rows": int(len(top_priority)),
        "priority_signal_counts": data["priority_signal"].value_counts().to_dict(),
        "state_summary_rows": int(len(state_summary)),
    }


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root", type=Path, default=root / "outputs" / "integrated"
    )
    parser.add_argument(
        "--output-root", type=Path, default=root / "outputs" / "rankings"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "stage": "Stage-II",
        "step": "territorial_rankings",
        "top_n": TOP_N,
        "ranking_notes": [
            "risk_rank solo se calcula para zonas con risk_score disponible.",
            "prediction_rank solo se calcula cuando existe predicción enlazada.",
            "prioridad_alta requiere riesgo alto y predicción en el cuartil superior.",
            "sin_historico no se mezcla con las prioridades confiables.",
        ],
        "scopes": [],
    }
    for scope in ("section", "municipality"):
        report["scopes"].append(
            build_scope_rankings(
                args.input_root / f"ccpc_{scope}_integrated.csv",
                args.output_root,
                scope,
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "ranking_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in report["scopes"]:
        print(
            f"{item['scope']}: {item['priority_candidate_rows']} candidatos "
            "prioritarios"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
