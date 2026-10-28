"""Genera un paquete visual ejecutivo y reproducible para el modelo CCPC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter, StrMethodFormatter


COLORS = {
    "navy": "#12304A",
    "blue": "#1769AA",
    "cyan": "#2A9DCC",
    "alto": "#C0392B",
    "medio": "#D97706",
    "bajo": "#238B6B",
    "base": "#5B6675",
    "intervencion": "#1769AA",
    "ink": "#17212B",
    "muted": "#667085",
    "grid": "#E5E7EB",
    "panel": "#F7F9FC",
    "white": "#FFFFFF",
}

RISK_LABELS = {"bajo": "Bajo", "medio": "Medio", "alto": "Alto"}
RISK_COLORS = {"bajo": COLORS["bajo"], "medio": COLORS["medio"], "alto": COLORS["alto"]}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.labelcolor": COLORS["ink"],
            "axes.edgecolor": COLORS["grid"],
            "axes.facecolor": COLORS["white"],
            "figure.facecolor": COLORS["white"],
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "text.color": COLORS["ink"],
            "savefig.dpi": 220,
            "savefig.bbox": "tight",
        }
    )


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=COLORS["white"])
    plt.close(fig)


def add_header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.06, 0.96, "INE · CCPC 2009–2024", fontsize=9, color=COLORS["blue"], weight="bold")
    fig.text(0.06, 0.915, title, fontsize=18, color=COLORS["navy"], weight="bold")
    fig.text(0.06, 0.88, subtitle, fontsize=9.5, color=COLORS["muted"])


def add_footer(fig: plt.Figure, text: str) -> None:
    fig.text(0.06, 0.025, text, fontsize=7.8, color=COLORS["muted"])


def style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["grid"])
    ax.spines["bottom"].set_color(COLORS["grid"])
    ax.grid(axis=grid_axis, color=COLORS["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def risk_distribution(risk: pd.DataFrame, output: Path, scope: str) -> None:
    counts = risk["risk_level"].value_counts().reindex(["bajo", "medio", "alto"]).fillna(0)
    shares = counts / len(risk)
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.subplots_adjust(top=0.78, bottom=0.17, left=0.1, right=0.95)
    add_header(fig, f"Semáforo territorial · {scope.title()}", "Distribución de zonas según el índice compuesto de riesgo")
    bars = ax.bar(
        [RISK_LABELS[x] for x in counts.index],
        counts.values,
        color=[RISK_COLORS[x] for x in counts.index],
        width=0.58,
    )
    ax.set_ylabel("Número de zonas")
    ax.set_xlabel("Nivel de riesgo")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    style_axes(ax)
    for bar, count, share in zip(bars, counts, shares):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{int(count):,}\n{share:.1%}",
                ha="center", va="bottom", fontsize=10, weight="bold")
    add_footer(fig, "Fuente: índice CCPC. El score orienta la priorización; no representa una probabilidad causal.")
    save_figure(fig, output / f"01_semaforo_{scope}.png")


def top_municipalities(risk: pd.DataFrame, output: Path) -> None:
    top = risk.nlargest(15, "risk_score").sort_values("risk_score")
    labels = [f"{row.MPIONOM.title()}, {row.EDONOM.title()}" for row in top.itertuples()]
    fig, ax = plt.subplots(figsize=(11, 8))
    fig.subplots_adjust(top=0.8, bottom=0.12, left=0.28, right=0.94)
    add_header(fig, "Municipios prioritarios", "Las 15 puntuaciones de riesgo más elevadas para focalizar diagnóstico")
    bars = ax.barh(labels, top["risk_score"], color=[RISK_COLORS[x] for x in top["risk_level"]], height=0.62)
    ax.set_xlabel("Puntuación compuesta de riesgo (0–100)")
    ax.set_xlim(0, 100)
    style_axes(ax, "x")
    ax.axvline(70, color=COLORS["alto"], linestyle="--", linewidth=1, alpha=0.8)
    ax.text(70.8, len(top) - 0.4, "Umbral alto: 70", color=COLORS["alto"], fontsize=8)
    for bar, value in zip(bars, top["risk_score"]):
        ax.text(value + 1.2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontsize=9)
    add_footer(fig, "Fuente: índice CCPC 2009–2024. Color: bajo, medio y alto según el nivel asignado.")
    save_figure(fig, output / "02_top_15_municipios_riesgo.png")


def scenario_comparison(scenario: pd.DataFrame, output: Path, scope: str) -> None:
    base = scenario["base_expected_abstainers"].sum() / scenario["latest_ln"].sum()
    intervention = scenario["intervention_expected_abstainers"].sum() / scenario["latest_ln"].sum()
    reduction = base - intervention
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.subplots_adjust(top=0.78, bottom=0.18)
    add_header(fig, f"Escenarios de abstención · {scope.title()}", "Comparación ponderada por lista nominal")
    bars = ax.bar(["Sin intervención", "Intervención hipotética"], [base, intervention],
                  color=[COLORS["base"], COLORS["intervencion"]], width=0.5)
    ax.set_ylabel("Abstención estimada")
    ax.set_xlabel("Escenario")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylim(0, max(base, intervention) * 1.3)
    style_axes(ax)
    for bar, value in zip(bars, [base, intervention]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.006, f"{value:.1%}",
                ha="center", va="bottom", fontsize=12, weight="bold")
    ax.text(0.5, max(base, intervention) * 1.16, f"Reducción simulada: {reduction:.1%}",
            ha="center", color=COLORS["intervencion"], fontsize=11, weight="bold")
    add_footer(fig, "Simulación paramétrica: +5 puntos porcentuales de participación en zonas prioritarias; no es una estimación causal.")
    save_figure(fig, output / f"03_escenarios_{scope}.png")


def state_priority(risk: pd.DataFrame, output: Path) -> pd.DataFrame:
    state = (
        risk.groupby("EDONOM", as_index=False)
        .agg(
            municipios=("MPIOCVE", "count"),
            riesgo_alto=("risk_level", lambda values: (values == "alto").sum()),
            puntuacion_promedio=("risk_score", "mean"),
            abstencion_promedio=("latest_abstention", "mean"),
        )
    )
    state["porcentaje_alto"] = state["riesgo_alto"] / state["municipios"]
    state["prioridad"] = state["porcentaje_alto"] * 0.6 + state["puntuacion_promedio"] / 100 * 0.4
    state = state.sort_values(["prioridad", "riesgo_alto"], ascending=False)
    state.to_csv(output / "ranking_entidades_prioridad.csv", index=False, encoding="utf-8-sig")
    plot = state.head(15).sort_values("prioridad")
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.subplots_adjust(top=0.8, bottom=0.15, left=0.25, right=0.93)
    add_header(fig, "Prioridad territorial por entidad", "Índice relativo: proporción de municipios en riesgo alto y score promedio")
    bars = ax.barh(plot["EDONOM"].str.title(), plot["prioridad"], color=COLORS["blue"], height=0.62)
    ax.set_xlabel("Índice relativo de prioridad (0–1)")
    ax.set_xlim(0, max(plot["prioridad"]) * 1.18)
    style_axes(ax, "x")
    for bar, value in zip(bars, plot["prioridad"]):
        ax.text(value + 0.005, bar.get_y() + bar.get_height() / 2, f"{value:.2f}", va="center", fontsize=9)
    add_footer(fig, "Fuente: riesgo municipal. La prioridad relativa no sustituye un diagnóstico operativo o presupuestal.")
    save_figure(fig, output / "04_prioridad_por_entidad.png")
    return state


def risk_vs_abstention(risk: pd.DataFrame, output: Path, scope: str) -> None:
    sample = risk.sample(min(8000, len(risk)), random_state=42) if len(risk) > 8000 else risk
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.subplots_adjust(top=0.79, bottom=0.15, left=0.1, right=0.95)
    add_header(fig, f"Riesgo compuesto frente a abstención reciente · {scope.title()}",
               "Cada punto representa una zona; el tamaño aproxima su lista nominal")
    for level in ["bajo", "medio", "alto"]:
        part = sample[sample["risk_level"] == level]
        ax.scatter(part["latest_abstention"], part["risk_score"], s=np.clip(part["latest_ln"] / 350, 8, 100),
                   alpha=0.42, color=RISK_COLORS[level], label=RISK_LABELS[level], edgecolors="none")
    ax.set_xlabel("Abstención reciente")
    ax.set_ylabel("Puntuación de riesgo (0–100)")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylim(0, 100)
    style_axes(ax)
    ax.legend(frameon=False, loc="lower right", title="Nivel")
    add_footer(fig, "Fuente: índice CCPC. Muestra visual de hasta 8,000 zonas; tamaño proporcional a lista nominal.")
    save_figure(fig, output / f"05_riesgo_vs_abstencion_{scope}.png")


def trend_volatility(risk: pd.DataFrame, output: Path, scope: str) -> None:
    sample = risk.sample(min(8000, len(risk)), random_state=7) if len(risk) > 8000 else risk
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.subplots_adjust(top=0.79, bottom=0.15, left=0.1, right=0.95)
    add_header(fig, f"Señales de deterioro y volatilidad · {scope.title()}",
               "La zona superior izquierda combina tendencia descendente y variabilidad elevada")
    colors = sample["risk_level"].map(RISK_COLORS)
    ax.scatter(sample["participation_slope"] * 100, sample["participation_volatility"] * 100,
               c=colors, alpha=0.38, s=22, edgecolors="none")
    ax.axvline(0, color=COLORS["muted"], linewidth=1)
    ax.set_xlabel("Pendiente de participación (puntos porcentuales por periodo)")
    ax.set_ylabel("Volatilidad histórica (puntos porcentuales)")
    style_axes(ax)
    ax.text(0.02, 0.95, "Tendencia descendente", transform=ax.transAxes, fontsize=8, color=COLORS["alto"])
    add_footer(fig, "Fuente: índice CCPC. Pendiente negativa indica disminución histórica de participación.")
    save_figure(fig, output / f"06_tendencia_vs_volatilidad_{scope}.png")


def scenario_impact(scenario: pd.DataFrame, output: Path, scope: str) -> None:
    impacted = scenario[scenario["expected_abstainers_avoided"] > 0].copy()
    quantiles = impacted["expected_abstainers_avoided"].quantile([0.25, 0.5, 0.75]).tolist()
    bins = [-1, quantiles[0], quantiles[1], quantiles[2], np.inf]
    labels = ["Bajo impacto", "Impacto medio-bajo", "Impacto medio-alto", "Alto impacto"]
    impacted["grupo_impacto"] = pd.cut(impacted["expected_abstainers_avoided"], bins=bins, labels=labels)
    counts = impacted["grupo_impacto"].value_counts().reindex(labels).fillna(0)
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.subplots_adjust(top=0.79, bottom=0.18)
    add_header(fig, f"Distribución del impacto simulado · {scope.title()}",
               "Zonas prioritarias agrupadas por abstenciones evitadas estimadas")
    bars = ax.bar(labels, counts, color=[COLORS["cyan"], COLORS["blue"], COLORS["navy"], COLORS["alto"]])
    ax.set_ylabel("Número de zonas prioritarias")
    ax.set_xlabel("Grupo de impacto")
    ax.tick_params(axis="x", rotation=12)
    style_axes(ax)
    for bar, value in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{int(value):,}", ha="center", va="bottom", weight="bold")
    add_footer(fig, "Fuente: escenario con uplift de 5 puntos porcentuales. Impacto expresado en personas estimadas, no observado.")
    save_figure(fig, output / f"07_distribucion_impacto_{scope}.png")


def avoided_by_state(scenario: pd.DataFrame, output: Path) -> None:
    state = scenario.groupby("EDONOM", as_index=False).agg(
        abstenciones_evitadas=("expected_abstainers_avoided", "sum"),
        zonas_prioritarias=("priority_zone", "sum"),
    ).sort_values("abstenciones_evitadas").tail(15)
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.subplots_adjust(top=0.8, bottom=0.15, left=0.23, right=0.94)
    add_header(fig, "Impacto potencial por entidad", "Abstenciones evitadas simuladas bajo el escenario de intervención")
    bars = ax.barh(state["EDONOM"].str.title(), state["abstenciones_evitadas"], color=COLORS["intervencion"])
    ax.set_xlabel("Abstenciones evitadas simuladas")
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    style_axes(ax, "x")
    for bar, value in zip(bars, state["abstenciones_evitadas"]):
        ax.text(value + max(state["abstenciones_evitadas"]) * 0.01,
                bar.get_y() + bar.get_height() / 2, f"{value:,.0f}", va="center", fontsize=8)
    add_footer(fig, "Fuente: escenario municipal. La magnitud depende de lista nominal y de la hipótesis de intervención.")
    save_figure(fig, output / "08_abstenciones_evitadas_por_entidad.png")


def prediction_quality(scenario: pd.DataFrame, output: Path, scope: str) -> None:
    data = scenario[["actual_abstention", "predicted_abstention"]].dropna()
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.subplots_adjust(top=0.79, bottom=0.15, left=0.12, right=0.95)
    add_header(fig, f"Calidad de la predicción · {scope.title()}", "Comparación entre abstención observada y estimada para 2024")
    ax.scatter(data["actual_abstention"], data["predicted_abstention"], s=14, alpha=0.28, color=COLORS["blue"])
    ax.plot([0, 1], [0, 1], linestyle="--", color=COLORS["muted"], linewidth=1.2, label="Predicción perfecta")
    mae = (data["actual_abstention"] - data["predicted_abstention"]).abs().mean()
    ax.text(0.05, 0.92, f"MAE visual: {mae:.3f}", transform=ax.transAxes, weight="bold", color=COLORS["navy"])
    ax.set_xlabel("Abstención observada")
    ax.set_ylabel("Abstención predicha")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    style_axes(ax)
    ax.legend(frameon=False, loc="lower right")
    add_footer(fig, "Fuente: predicciones fuera de muestra del modelo temporal. MAE = error absoluto medio.")
    save_figure(fig, output / f"09_calidad_prediccion_{scope}.png")


def historical_trend(analytical: pd.DataFrame, output: Path, scope: str) -> None:
    grouped = (
        analytical.groupby("AELEC", as_index=False)
        .apply(
            lambda frame: pd.Series(
                {
                    "participacion": np.average(frame["participation_rate"], weights=frame["LN"]),
                    "abstencion": np.average(frame["abstention_rate"], weights=frame["LN"]),
                    "no_especificado": np.average(frame["non_specified_rate"], weights=frame["LN"]),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    grouped["AELEC"] = sorted(analytical["AELEC"].unique())
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.subplots_adjust(top=0.79, bottom=0.16, left=0.1, right=0.95)
    add_header(fig, f"Evolución histórica de participación · {scope.title()}",
               "Tasas ponderadas por lista nominal en los seis ejercicios CCPC disponibles")
    ax.plot(grouped["AELEC"], grouped["participacion"], marker="o", linewidth=2.5,
            color=COLORS["intervencion"], label="Participación")
    ax.plot(grouped["AELEC"], grouped["abstencion"], marker="o", linewidth=2.5,
            color=COLORS["alto"], label="Abstención")
    ax.plot(grouped["AELEC"], grouped["no_especificado"], marker="o", linewidth=1.8,
            color=COLORS["medio"], label="No especificado")
    ax.set_xlabel("Año del ejercicio CCPC")
    ax.set_ylabel("Tasa ponderada")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xticks(grouped["AELEC"])
    ax.set_ylim(0, 1)
    style_axes(ax)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.02))
    for _, row in grouped.iterrows():
        ax.text(row["AELEC"], row["abstencion"] + 0.025, f"{row['abstencion']:.1%}",
                ha="center", fontsize=8, color=COLORS["alto"])
    add_footer(fig, "Fuente: dataset analítico CCPC 2009–2024. Las tasas se agregan ponderando por lista nominal.")
    save_figure(fig, output / f"11_evolucion_historica_{scope}.png")


def model_comparison(metrics_path: Path, output: Path, scope: str) -> None:
    report = json.loads(metrics_path.read_text(encoding="utf-8"))
    models = report["models"]
    names = {"persistence_baseline": "Persistencia", "ridge": "Ridge", "hist_gradient_boosting": "Gradient Boosting"}
    labels = [names[key] for key in models]
    mae = [models[key]["mae"] for key in models]
    rmse = [models[key]["rmse"] for key in models]
    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.subplots_adjust(top=0.79, bottom=0.16)
    add_header(fig, f"Comparación de modelos · {scope.title()}",
               "Menor error indica una predicción más cercana a la abstención observada")
    bars1 = ax.bar(x - width / 2, mae, width, label="MAE", color=COLORS["blue"])
    bars2 = ax.bar(x + width / 2, rmse, width, label="RMSE", color=COLORS["cyan"])
    ax.set_xticks(x, labels)
    ax.set_ylabel("Error (proporción)")
    ax.set_xlabel("Modelo")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylim(0, max(rmse) * 1.35)
    style_axes(ax)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    for bars in [bars1, bars2]:
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                    f"{bar.get_height():.1%}", ha="center", fontsize=8)
    add_footer(fig, f"Fuente: validación temporal fuera de muestra hasta {report['target_year']}. MAE y RMSE son métricas de error.")
    save_figure(fig, output / f"12_comparacion_modelos_{scope}.png")


def sensitivity_curve(scenario_json: Path, output: Path, scope: str) -> None:
    report = json.loads(scenario_json.read_text(encoding="utf-8"))
    sensitivity = report["sensitivity"]
    uplifts = [item["assumptions"]["intervention"].split("absolute ")[1].split("%")[0] for item in sensitivity]
    uplifts = [float(value) / 100 for value in uplifts]
    avoided = [item["expected_abstainers_avoided"] for item in sensitivity]
    base = [item["base_weighted_abstention"] for item in sensitivity]
    intervention = [item["intervention_weighted_abstention"] for item in sensitivity]
    fig, ax1 = plt.subplots(figsize=(10, 6.5))
    fig.subplots_adjust(top=0.79, bottom=0.16, left=0.1, right=0.88)
    add_header(fig, f"Sensibilidad de la intervención · {scope.title()}",
               "Qué cambia si el uplift hipotético pasa de 2 a 10 puntos porcentuales")
    line1 = ax1.plot(uplifts, base, marker="o", color=COLORS["base"], linewidth=2, label="Abstención base")
    line2 = ax1.plot(uplifts, intervention, marker="o", color=COLORS["intervencion"], linewidth=2, label="Abstención intervenida")
    ax1.set_xlabel("Uplift de participación hipotético")
    ax1.set_ylabel("Abstención ponderada")
    ax1.xaxis.set_major_formatter(PercentFormatter(1))
    ax1.yaxis.set_major_formatter(PercentFormatter(1))
    style_axes(ax1)
    ax2 = ax1.twinx()
    line3 = ax2.plot(uplifts, avoided, marker="s", linestyle="--", color=COLORS["alto"], linewidth=2, label="Abstenciones evitadas")
    ax2.set_ylabel("Abstenciones evitadas simuladas")
    ax2.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax2.spines["top"].set_visible(False)
    lines = line1 + line2 + line3
    ax1.legend(lines, [line.get_label() for line in lines], frameon=False, loc="upper right")
    add_footer(fig, "Fuente: sensibilidad de escenarios. No representa una relación causal ni una estimación de costo-efectividad.")
    save_figure(fig, output / f"13_sensibilidad_intervencion_{scope}.png")


def heatmap_risk_components(risk: pd.DataFrame, output: Path, scope: str) -> None:
    component_cols = {
        "Abstención reciente": "recent_abstention_percentile",
        "Tendencia descendente": "declining_trend_percentile",
        "Volatilidad": "volatility_percentile",
        "No especificado": "non_specified_percentile",
    }
    selected = risk.nlargest(15, "risk_score").copy().sort_values("risk_score")
    matrix = selected[list(component_cols.values())].to_numpy()
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.subplots_adjust(top=0.8, bottom=0.14, left=0.34, right=0.93)
    add_header(fig, f"Perfil de factores de riesgo · {scope.title()}",
               "Percentiles de los componentes que explican la puntuación compuesta")
    cmap = LinearSegmentedColormap.from_list("risk", [COLORS["panel"], "#F2C14E", COLORS["alto"]])
    image = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=100)
    ax.set_xticks(range(len(component_cols)), component_cols.keys(), rotation=25, ha="right")
    labels = [f"{row.MPIONOM.title()}, {row.EDONOM.title()}" for row in selected.itertuples()]
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Componente del índice")
    ax.set_ylabel("Zona prioritaria")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.0f}", ha="center", va="center", fontsize=8,
                    color=COLORS["white"] if matrix[i, j] > 65 else COLORS["ink"])
    fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02, label="Percentil (0–100)")
    add_footer(fig, "Fuente: índice CCPC. Un percentil alto indica una señal relativamente más intensa dentro de las zonas analizadas.")
    save_figure(fig, output / f"10_componentes_riesgo_{scope}.png")


def executive_dashboard(risk: pd.DataFrame, scenario: pd.DataFrame, output: Path, scope: str) -> None:
    counts = risk["risk_level"].value_counts()
    base = scenario["base_expected_abstainers"].sum() / scenario["latest_ln"].sum()
    intervention = scenario["intervention_expected_abstainers"].sum() / scenario["latest_ln"].sum()
    avoided = scenario["expected_abstainers_avoided"].sum()
    fig = plt.figure(figsize=(13, 8))
    fig.subplots_adjust(top=0.83, bottom=0.09, left=0.06, right=0.96, hspace=0.45, wspace=0.28)
    add_header(fig, f"Tablero ejecutivo · {scope.title()}", "Lectura rápida para priorización, diagnóstico y planeación preventiva")
    cards = [
        ("Zonas analizadas", f"{len(risk):,}", COLORS["navy"]),
        ("Riesgo alto", f"{int(counts.get('alto', 0)):,} · {counts.get('alto', 0) / len(risk):.1%}", COLORS["alto"]),
        ("Abstención base", f"{base:.1%}", COLORS["base"]),
        ("Abstenciones evitadas", f"{avoided:,.0f}", COLORS["intervencion"]),
    ]
    for i, (label, value, color) in enumerate(cards):
        ax = fig.add_axes([0.06 + i * 0.235, 0.70, 0.20, 0.11])
        ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=COLORS["panel"], edgecolor=COLORS["grid"], linewidth=1))
        ax.add_patch(Rectangle((0, 0), 0.018, 1, facecolor=color, edgecolor=color))
        ax.text(0.08, 0.65, label, fontsize=8.5, color=COLORS["muted"])
        ax.text(0.08, 0.25, value, fontsize=17, weight="bold", color=COLORS["navy"])
        ax.axis("off")
    ax1 = fig.add_subplot(2, 2, 3)
    risk_counts = counts.reindex(["bajo", "medio", "alto"]).fillna(0)
    ax1.bar([RISK_LABELS[x] for x in risk_counts.index], risk_counts.values,
            color=[RISK_COLORS[x] for x in risk_counts.index])
    ax1.set_title("Semáforo territorial", loc="left", fontsize=12)
    ax1.set_ylabel("Zonas")
    style_axes(ax1)
    ax2 = fig.add_subplot(2, 2, 4)
    ax2.bar(["Base", "Intervención"], [base, intervention], color=[COLORS["base"], COLORS["intervencion"]], width=0.5)
    ax2.set_title("Escenario de abstención", loc="left", fontsize=12)
    ax2.set_ylabel("Abstención")
    ax2.yaxis.set_major_formatter(PercentFormatter(1))
    style_axes(ax2)
    for x, value in enumerate([base, intervention]):
        ax2.text(x, value + 0.008, f"{value:.1%}", ha="center", weight="bold")
    add_footer(fig, "Fuente: CCPC 2009–2024 y simulación paramétrica. Las cifras de intervención son hipotéticas y deben validarse localmente.")
    save_figure(fig, output / f"00_tablero_ejecutivo_{scope}.png")


def write_summary(risk: pd.DataFrame, scenario: pd.DataFrame, output: Path, scope: str) -> None:
    base = scenario["base_expected_abstainers"].sum() / scenario["latest_ln"].sum()
    intervention = scenario["intervention_expected_abstainers"].sum() / scenario["latest_ln"].sum()
    counts = risk["risk_level"].value_counts()
    files = sorted(path.name for path in output.glob("*.png"))
    lines = [
        f"# Paquete visual — {scope}",
        "",
        "## Indicadores principales",
        "",
        f"- Zonas analizadas: **{len(risk):,}**.",
        f"- Riesgo alto: **{int(counts.get('alto', 0)):,}** ({counts.get('alto', 0) / len(risk):.1%}).",
        f"- Riesgo medio: **{int(counts.get('medio', 0)):,}** ({counts.get('medio', 0) / len(risk):.1%}).",
        f"- Riesgo bajo: **{int(counts.get('bajo', 0)):,}** ({counts.get('bajo', 0) / len(risk):.1%}).",
        f"- Abstención sin intervención: **{base:.1%}**.",
        f"- Abstención con intervención hipotética: **{intervention:.1%}**.",
        f"- Abstenciones evitadas simuladas: **{scenario['expected_abstainers_avoided'].sum():,.0f}**.",
        "",
        "## Archivos generados",
        "",
        *[f"- `{name}`" for name in files],
        "",
        "## Lectura responsable",
        "",
        "Las visualizaciones sirven para priorizar diagnóstico y planeación. El score no es una certeza "
        "causal; la intervención de 5 puntos porcentuales es una hipótesis de simulación.",
    ]
    (output / f"README_{scope}.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--risk-root", type=Path, default=root / "outputs" / "risk")
    parser.add_argument("--scenarios-root", type=Path, default=root / "outputs" / "scenarios")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "graficas")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_style()
    args.output_root.mkdir(parents=True, exist_ok=True)
    municipal_risk = pd.read_csv(args.risk_root / "ccpc_municipality_risk.csv", low_memory=False)
    municipal_scenario = pd.read_csv(args.scenarios_root / "ccpc_municipality_scenarios.csv", low_memory=False)
    section_risk = pd.read_csv(args.risk_root / "ccpc_section_risk.csv", low_memory=False)
    section_scenario = pd.read_csv(args.scenarios_root / "ccpc_section_scenarios.csv", low_memory=False)
    municipal_history = pd.read_csv(args.risk_root.parent / "analytical" / "ccpc_municipality_year.csv", low_memory=False)
    section_history = pd.read_csv(args.risk_root.parent / "analytical" / "ccpc_section_year.csv", low_memory=False)
    municipal_metrics = args.risk_root.parent / "models" / "ccpc_municipality_model_metrics.json"
    section_metrics = args.risk_root.parent / "models" / "ccpc_section_model_metrics.json"
    municipal_sensitivity = args.scenarios_root / "ccpc_municipality_scenarios.json"
    section_sensitivity = args.scenarios_root / "ccpc_section_scenarios.json"

    for risk, scenario, scope in [
        (municipal_risk, municipal_scenario, "municipios"),
        (section_risk, section_scenario, "secciones"),
    ]:
        executive_dashboard(risk, scenario, args.output_root, scope)
        risk_distribution(risk, args.output_root, scope)
        risk_vs_abstention(risk, args.output_root, scope)
        trend_volatility(risk, args.output_root, scope)
        scenario_comparison(scenario, args.output_root, scope)
        scenario_impact(scenario, args.output_root, scope)
        prediction_quality(scenario, args.output_root, scope)
        historical_trend(municipal_history if scope == "municipios" else section_history, args.output_root, scope)
        model_comparison(municipal_metrics if scope == "municipios" else section_metrics, args.output_root, scope)
        sensitivity_curve(municipal_sensitivity if scope == "municipios" else section_sensitivity, args.output_root, scope)
        heatmap_risk_components(risk, args.output_root, scope)
        write_summary(risk, scenario, args.output_root, scope)

    top_municipalities(municipal_risk, args.output_root)
    state_priority(municipal_risk, args.output_root)
    avoided_by_state(municipal_scenario, args.output_root)
    print(f"Paquete visual ejecutivo generado en {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
