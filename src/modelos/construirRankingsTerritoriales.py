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
        "historico_confiable",
        "abstencion_predicha",
        "prediccion_disponible",
        "abstencion_reciente",
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
    data["rango_prediccion"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    predicted = data["abstencion_predicha"].notna()
    data.loc[predicted, "rango_prediccion"] = (
        data.loc[predicted, "abstencion_predicha"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

    prediction_high_threshold = data.loc[predicted, "abstencion_predicha"].quantile(
        0.75
    )
    data["señal_prioridad"] = "seguimiento"
    data.loc[~data["historico_confiable"], "señal_prioridad"] = "sin_historico"
    data.loc[
        data["historico_confiable"] & data["indiceRiesgo_level"].eq("alto"), "señal_prioridad"
    ] = "riesgo_alto"
    data.loc[
        data["historico_confiable"]
        & data["abstencion_predicha"].ge(prediction_high_threshold),
        "señal_prioridad",
    ] = "prediccion_alta"
    data.loc[
        data["historico_confiable"]
        & data["indiceRiesgo_level"].eq("alto")
        & data["abstencion_predicha"].ge(prediction_high_threshold),
        "señal_prioridad",
    ] = "riesgo_alto_y_prediccion_alta"

    output_root.mkdir(parents=True, exist_ok=True)
    top_indiceRiesgo = data.loc[reliable].sort_values(
        ["indiceRiesgo_score"] + columnasRanking(scope),
        ascending=[False] + [True] * len(columnasRanking(scope)),
    ).head(TOP_N)
    top_prediction = data.loc[predicted].sort_values(
        ["abstencion_predicha"] + columnasRanking(scope),
        ascending=[False] + [True] * len(columnasRanking(scope)),
    ).head(TOP_N)
    top_priority = data.loc[
        data["señal_prioridad"].eq("riesgo_alto_y_prediccion_alta")
    ].sort_values(
        ["indiceRiesgo_score", "abstencion_predicha"] + columnasRanking(scope),
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
            reliable_zones=("historico_confiable", "sum"),
            high_indiceRiesgo_zones=("indiceRiesgo_level", lambda values: (values == "alto").sum()),
            predicted_zones=("prediccion_disponible", "sum"),
            mean_indiceRiesgo_score=("indiceRiesgo_score", "mean"),
            mean_abstencionPredicha=("abstencion_predicha", "mean"),
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
        "prediccion_disponible_zones": int(predicted.sum()),
        "prediction_high_threshold": float(prediction_high_threshold),
        "top_indiceRiesgo_rows": int(len(top_indiceRiesgo)),
        "top_prediction_rows": int(len(top_prediction)),
        "priority_candidate_rows": int(len(top_priority)),
        "señal_prioridad_counts": data["señal_prioridad"].value_counts().to_dict(),
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
            "rango_prediccion solo se calcula cuando existe predicción enlazada.",
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
