"""Genera resultados ejecutivos completamente en español."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def pct(value: float) -> str:
    return f"{value:.1%}"


def zone_name(row: pd.Series) -> str:
    state = row.get("EDONOM", "Entidad no disponible")
    municipality = row.get("MPIONOM", "Municipio no disponible")
    section = row.get("SECCION")
    if pd.notna(section):
        return f"Sección {int(section)} de {municipality}, {state}"
    return f"{municipality}, {state}"


def risk_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if row["latest_abstention"] >= 0.60:
        reasons.append(f"abstención reciente muy alta ({pct(row['latest_abstention'])})")
    elif row["latest_abstention"] >= 0.40:
        reasons.append(f"abstención reciente alta ({pct(row['latest_abstention'])})")
    if row["participation_slope"] <= -0.01:
        reasons.append("participación en descenso marcado")
    elif row["participation_slope"] < 0:
        reasons.append("participación con tendencia descendente")
    if row["participation_volatility"] >= 0.10:
        reasons.append("comportamiento histórico muy variable")
    elif row["participation_volatility"] >= 0.05:
        reasons.append("variación histórica relevante")
    if row["latest_non_specified"] >= 0.10:
        reasons.append(f"proporción no especificada elevada ({pct(row['latest_non_specified'])})")
    if not reasons:
        reasons.append("no presenta señales históricas fuertes de abstención")
    return "; ".join(reasons)


def recommendation(level: str, reason: str) -> str:
    if level == "alto":
        return "Priorizar diagnóstico local, promoción de participación y seguimiento antes de la jornada."
    if level == "medio":
        return "Monitorear la zona y preparar acciones preventivas focalizadas si las señales empeoran."
    return "Mantener monitoreo básico y documentar buenas prácticas de participación."


def translate_risk_level(value: object) -> str:
    return {"bajo": "Bajo", "medio": "Medio", "alto": "Alto"}.get(str(value), str(value))


def spanish_columns(data: pd.DataFrame) -> pd.DataFrame:
    return data.rename(
        columns={
            "zone_name": "Zona",
            "EDOCVE": "Clave de entidad",
            "MPIOCVE": "Clave de municipio",
            "EDONOM": "Entidad",
            "MPIONOM": "Municipio",
            "SECCION": "Sección electoral",
            "TIPOSEC": "Tipo de sección",
            "risk_score": "Puntuación de riesgo",
            "risk_level": "Nivel de riesgo",
            "latest_abstention": "Abstención 2024",
            "latest_participation": "Participación 2024",
            "participation_slope": "Tendencia de participación",
            "participation_volatility": "Variabilidad histórica",
            "latest_non_specified": "No especificado 2024",
            "years_observed": "Años observados",
            "trend_reliable": "Tendencia confiable",
            "predicted_abstention": "Abstención predicha",
            "predicted_risk_level": "Nivel de riesgo predicho",
            "actual_abstention": "Abstención observada",
            "prediction_error": "Error de predicción",
            "base_abstention": "Abstención sin intervención",
            "intervention_abstention": "Abstención con intervención",
            "abstention_reduction": "Reducción simulada de abstención",
            "expected_abstainers_avoided": "Abstenciones evitadas simuladas",
            "priority_zone": "Zona prioritaria",
            "base_risk_level": "Riesgo sin intervención",
            "intervention_risk_level": "Riesgo con intervención",
            "risk_reason": "Justificación del riesgo",
            "recommended_action": "Acción recomendada",
            "prediction_reason": "Justificación de la predicción",
            "scenario_reason": "Justificación del escenario",
            "interpretation": "Interpretación sencilla",
        }
    )


def build_risk_report(risk_path: Path, output: Path, scope: str) -> pd.DataFrame:
    risk = pd.read_csv(risk_path, low_memory=False)
    risk["zone_name"] = risk.apply(zone_name, axis=1)
    risk["risk_reason"] = risk.apply(risk_reason, axis=1)
    risk["recommended_action"] = risk.apply(
        lambda row: recommendation(row["risk_level"], row["risk_reason"]), axis=1
    )
    risk["interpretation"] = risk.apply(
        lambda row: (
            f"{row['zone_name']} tiene riesgo {row['risk_level']} "
            f"(score {row['risk_score']:.1f}/100). Razón: {row['risk_reason']}."
        ),
        axis=1,
    )
    columns = [
        "zone_name",
        "EDONOM",
        "MPIONOM",
        "risk_score",
        "risk_level",
        "latest_abstention",
        "latest_participation",
        "participation_slope",
        "participation_volatility",
        "latest_non_specified",
        "years_observed",
        "trend_reliable",
        "risk_reason",
        "recommended_action",
        "interpretation",
    ]
    if "SECCION" in risk:
        columns.insert(2, "SECCION")
    output.parent.mkdir(parents=True, exist_ok=True)
    output_data = risk.sort_values("risk_score", ascending=False)[columns].copy()
    output_data["risk_level"] = output_data["risk_level"].map(translate_risk_level)
    spanish_columns(output_data).to_csv(output, index=False)
    return risk


def build_model_report(prediction_path: Path, risk: pd.DataFrame, output: Path) -> pd.DataFrame:
    predictions = pd.read_csv(prediction_path, low_memory=False)
    keys = ["EDOCVE", "MPIOCVE"] + (["SECCION", "TIPOSEC"] if "SECCION" in predictions else [])
    metadata = risk[keys + ["zone_name", "risk_reason", "recommended_action"]].drop_duplicates(keys)
    result = predictions.merge(metadata, on=keys, how="left", validate="one_to_one")
    result["prediction_reason"] = result.apply(
        lambda row: (
            f"Predicción de abstención de {pct(row['predicted_abstention'])}; "
            f"la zona presenta {row['risk_reason']}."
        ),
        axis=1,
    )
    result["interpretation"] = result.apply(
        lambda row: (
            f"{row['zone_name']}: abstención esperada {pct(row['predicted_abstention'])} "
            f"({row['predicted_risk_level']}). {row['prediction_reason']}"
        ),
        axis=1,
    )
    columns = keys + [
        "zone_name",
        "predicted_abstention",
        "predicted_risk_level",
        "actual_abstention",
        "prediction_error",
        "risk_reason",
        "prediction_reason",
        "recommended_action",
        "interpretation",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output_data = result.sort_values("predicted_abstention", ascending=False)[columns].copy()
    output_data["predicted_risk_level"] = output_data["predicted_risk_level"].map(
        translate_risk_level
    )
    spanish_columns(output_data).to_csv(output, index=False)
    return result


def build_scenario_report(scenario_path: Path, output: Path) -> pd.DataFrame:
    data = pd.read_csv(scenario_path, low_memory=False)
    data["zone_name"] = data.apply(zone_name, axis=1)
    data["scenario_reason"] = np.where(
        data["priority_zone"],
        "Zona prioritaria por puntuación de riesgo alta o abstención predicha de al menos 40%.",
        "Zona no prioritaria bajo la regla actual de intervención.",
    )
    data["interpretation"] = data.apply(
        lambda row: (
            f"{row['zone_name']}: escenario base {pct(row['base_abstention'])} de abstención; "
            f"con intervención {pct(row['intervention_abstention'])}. "
            f"Reducción simulada: {pct(row['abstention_reduction'])}. "
            f"{row['scenario_reason']}"
        ),
        axis=1,
    )
    columns = [
        "zone_name",
        "base_abstention",
        "intervention_abstention",
        "abstention_reduction",
        "expected_abstainers_avoided",
        "priority_zone",
        "base_risk_level",
        "intervention_risk_level",
        "scenario_reason",
        "interpretation",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output_data = data.sort_values(
        ["priority_zone", "expected_abstainers_avoided"],
        ascending=[False, False],
    )[columns].copy()
    for column in ("base_risk_level", "intervention_risk_level"):
        output_data[column] = output_data[column].map(translate_risk_level)
    spanish_columns(output_data).to_csv(output, index=False)
    return data


def build_summary(output: Path, risk_reports: dict[str, pd.DataFrame]) -> None:
    sections = []
    for scope, data in risk_reports.items():
        counts = data["risk_level"].value_counts()
        sections.append(
            f"## {'Secciones electorales' if scope == 'section' else 'Municipios'}\n\n"
            f"- Zonas analizadas: {len(data):,}\n"
            f"- Riesgo alto: {int(counts.get('alto', 0)):,} "
            f"({counts.get('alto', 0) / len(data):.1%})\n"
            f"- Riesgo medio: {int(counts.get('medio', 0)):,} "
            f"({counts.get('medio', 0) / len(data):.1%})\n"
            f"- Riesgo bajo: {int(counts.get('bajo', 0)):,} "
            f"({counts.get('bajo', 0) / len(data):.1%})\n\n"
            "Cada fila del reporte incluye la zona, métricas observadas, razón del nivel "
            "y acción sugerida."
        )
    output.write_text(
        "# Resultados explicados del modelo CCPC\n\n"
        "Los reportes técnicos se conservaron. Estos archivos agregan una lectura sencilla "
        "para toma de decisiones. Riesgo no significa certeza ni predicción individual.\n\n"
        + "\n\n".join(sections),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--risk-root", type=Path, default=root / "outputs" / "risk")
    parser.add_argument("--models-root", type=Path, default=root / "outputs" / "models")
    parser.add_argument("--scenarios-root", type=Path, default=root / "outputs" / "scenarios")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "ejecutivo")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    risk_reports: dict[str, pd.DataFrame] = {}
    for scope in ("section", "municipality"):
        risk = build_risk_report(
            args.risk_root / f"ccpc_{scope}_risk.csv",
            args.output_root / f"ccpc_{scope}_riesgo_explicado.csv",
            scope,
        )
        risk_reports[scope] = risk
        build_model_report(
            args.models_root / f"ccpc_{scope}_predictions_2024.csv",
            risk,
            args.output_root / f"ccpc_{scope}_predicciones_explicadas.csv",
        )
        build_scenario_report(
            args.scenarios_root / f"ccpc_{scope}_scenarios.csv",
            args.output_root / f"ccpc_{scope}_escenarios_explicados.csv",
        )
    build_summary(args.output_root / "README.md", risk_reports)
    print("Reportes ejecutivos explicados generados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
