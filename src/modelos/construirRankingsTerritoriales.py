"""Construye rankings territoriales transparentes a partir de resultados integrados."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


TOP_N = 100
RISK_LEVELS = ("alto", "medio", "bajo")


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def columnasRanking(scope: str) -> list[str]:
    columns = ["EDONOM", "MPIONOM"]
    if scope == "section":
        columns += ["SECCION", "TIPOSEC"]
    return columns


def construirRankingsAlcance(
    input_path: Path, output_root: Path, scope: str
) -> dict[str, object]:
    data = pd.read_csv(input_path, low_memory=False)
    required = columnasRanking(scope) + [
        "indiceRiesgo_score",
        "indiceRiesgo_level",
        "indiceRiesgo_reason",
        "trend_reliable",
        "predicted_abstention",
        "prediction_available",
        "latest_abstention",
    ]
    missing = [column for column in required if column not in data]
    if missing:
        raise ValueError(f"Faltan columnas en {input_path}: {missing}")

    data = data.copy()
    data["indiceRiesgo_rank"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    reliable = data["indiceRiesgo_score"].notna()
    data.loc[reliable, "indiceRiesgo_rank"] = (
        data.loc[reliable, "indiceRiesgo_score"]
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
        data["trend_reliable"] & data["indiceRiesgo_level"].eq("alto"), "priority_signal"
    ] = "riesgo_alto"
    data.loc[
        data["trend_reliable"]
        & data["predicted_abstention"].ge(prediction_high_threshold),
        "priority_signal",
    ] = "prediccion_alta"
    data.loc[
        data["trend_reliable"]
        & data["indiceRiesgo_level"].eq("alto")
        & data["predicted_abstention"].ge(prediction_high_threshold),
        "priority_signal",
    ] = "riesgo_alto_y_prediccion_alta"

    output_root.mkdir(parents=True, exist_ok=True)
    top_indiceRiesgo = data.loc[reliable].sort_values(
        ["indiceRiesgo_score"] + columnasRanking(scope),
        ascending=[False] + [True] * len(columnasRanking(scope)),
    ).head(TOP_N)
    top_prediction = data.loc[predicted].sort_values(
        ["predicted_abstention"] + columnasRanking(scope),
        ascending=[False] + [True] * len(columnasRanking(scope)),
    ).head(TOP_N)
    top_priority = data.loc[
        data["priority_signal"].eq("riesgo_alto_y_prediccion_alta")
    ].sort_values(
        ["indiceRiesgo_score", "predicted_abstention"] + columnasRanking(scope),
        ascending=[False, False] + [True] * len(columnasRanking(scope)),
    ).head(TOP_N)

    top_indiceRiesgo.to_csv(output_root / f"top_{scope}_by_indiceRiesgo.csv", index=False)
    top_prediction.to_csv(
        output_root / f"top_{scope}_by_abstencionPredicha.csv", index=False
    )
    top_priority.to_csv(
        output_root / f"top_{scope}_priority_candidates.csv", index=False
    )

    state_summary = (
        data.groupby("EDONOM", dropna=False)
        .agg(
            zones=("EDONOM", "size"),
            reliable_zones=("trend_reliable", "sum"),
            high_indiceRiesgo_zones=("indiceRiesgo_level", lambda values: (values == "alto").sum()),
            predicted_zones=("prediction_available", "sum"),
            mean_indiceRiesgo_score=("indiceRiesgo_score", "mean"),
            mean_abstencionPredicha=("predicted_abstention", "mean"),
        )
        .reset_index()
        .sort_values(["high_indiceRiesgo_zones", "mean_indiceRiesgo_score"], ascending=[False, False])
    )
    state_summary.to_csv(output_root / f"{scope}_state_summary.csv", index=False)

    return {
        "scope": scope,
        "input": str(input_path),
        "zones": int(len(data)),
        "reliable_zones": int(reliable.sum()),
        "prediction_available_zones": int(predicted.sum()),
        "prediction_high_threshold": float(prediction_high_threshold),
        "top_indiceRiesgo_rows": int(len(top_indiceRiesgo)),
        "top_prediction_rows": int(len(top_prediction)),
        "priority_candidate_rows": int(len(top_priority)),
        "priority_signal_counts": data["priority_signal"].value_counts().to_dict(),
        "state_summary_rows": int(len(state_summary)),
    }


def interpretarArgumentos() -> argparse.Namespace:
    root = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root", type=Path, default=root / "outputs" / "resultadosIntegrados"
    )
    parser.add_argument(
        "--output-root", type=Path, default=root / "outputs" / "rankings"
    )
    return parser.parse_args()


def main() -> int:
    args = interpretarArgumentos()
    report = {
        "project_area": "territorial_rankings",
        "step": "territorial_rankings",
        "top_n": TOP_N,
        "ranking_notes": [
            "indiceRiesgo_rank solo se calcula para zonas con indiceRiesgo_score disponible.",
            "prediction_rank solo se calcula cuando existe predicción enlazada.",
            "prioridad_alta requiere riesgo alto y predicción en el cuartil superior.",
            "sin_historico no se mezcla con las prioridades confiables.",
        ],
        "scopes": [],
    }
    for scope in ("section", "municipality"):
        report["scopes"].append(
            construirRankingsAlcance(
                args.input_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}ResultadosIntegrados.csv",
                args.output_root,
                scope,
            )
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "manifiestoRankings.json").write_text(
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
