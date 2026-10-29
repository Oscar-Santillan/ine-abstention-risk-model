"""Empaqueta datos y gr?ficas por entidad federativa."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {"navy": "#17324D", "blue": "#2F6B9A", "red": "#C84B4B", "gray": "#8996A3"}
RISK_COLORS = {"bajo": "#4E8B57", "medio": "#D99A2B", "alto": "#C84B4B", "sin_historico": "#8996A3"}


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def nombreSeguro(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def configurarMatplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#D7DEE5",
            "axes.labelcolor": COLORS["navy"],
            "grid.color": "#DCE3E9",
            "grid.alpha": 0.8,
        }
    )


def guardarGrafica(fig: plt.Figure, folder: Path, name: str) -> list[str]:
    fig.tight_layout(pad=1.2)
    paths = [folder / f"{name}.png", folder / f"{name}.pdf"]
    for path in paths:
        fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return [path.name for path in paths]


def escribirAlcance(entity: str, data: pd.DataFrame, folder: Path, scope: str) -> list[str]:
    scoped = data.loc[data["EDONOM"].eq(entity)].copy()
    scoped.to_csv(folder / f"{scope}_datos.csv", index=False)
    charts = []

    counts = scoped["indiceRiesgo_level"].value_counts().reindex(
        ["bajo", "medio", "alto", "sin_historico"], fill_value=0
    )
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(
        ["Bajo", "Medio", "Alto", "Sin histórico"],
        counts.values,
        color=[RISK_COLORS[x] for x in counts.index],
    )
    ax.set_title(f"{entity} · Semáforo de riesgo · {scope.title()}", loc="left")
    ax.set_xlabel("Nivel")
    ax.set_ylabel("Número de zonas")
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.bar_label(bars, labels=[f"{x:,}" for x in counts.values], padding=4)
    charts += guardarGrafica(fig, folder, f"{scope}_distribucion_riesgo")

    ranked = scoped.loc[scoped["indiceRiesgo_score"].notna()].nlargest(10, "indiceRiesgo_score").sort_values("indiceRiesgo_score")
    if not ranked.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = ranked["MPIONOM"].astype(str)
        if "SECCION" in ranked:
            labels = labels + " · sección " + ranked["SECCION"].astype(str)
        ax.barh(labels, ranked["indiceRiesgo_score"], color=COLORS["red"])
        ax.set_title(f"{entity} · Zonas prioritarias · {scope.title()}", loc="left")
        ax.set_xlabel("Índice de riesgo (0–100)")
        ax.set_xlim(0, 100)
        ax.grid(axis="x")
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        charts += guardarGrafica(fig, folder, f"{scope}_top_riesgo")
    return charts


def main() -> int:
    root = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "resultadosIntegrados")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "entidades")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    configurarMatplotlib()

    section = pd.read_csv(args.input_root / "ccpc_seccionResultadosIntegrados.csv", low_memory=False)
    municipality = pd.read_csv(args.input_root / "ccpc_municipioResultadosIntegrados.csv", low_memory=False)
    entities = sorted(set(section["EDONOM"].dropna()) | set(municipality["EDONOM"].dropna()))
    report = {"descripcion": "Paquete territorial por entidad federativa", "entidades": [], "total_paquetes": len(entities) + 1}

    for entity in entities:
        folder = args.output_root / nombreSeguro(entity)
        folder.mkdir(parents=True, exist_ok=True)
        charts = escribirAlcance(entity, section, folder, "secciones")
        charts += escribirAlcance(entity, municipality, folder, "municipios")
        summary = {
            "entidad": entity,
            "secciones": int((section["EDONOM"] == entity).sum()),
            "municipios": int((municipality["EDONOM"] == entity).sum()),
            "secciones_con_score": int(section.loc[section["EDONOM"].eq(entity), "indiceRiesgo_score"].notna().sum()),
            "municipios_con_score": int(municipality.loc[municipality["EDONOM"].eq(entity), "indiceRiesgo_score"].notna().sum()),
            "graficas": charts,
        }
        (folder / "resumen.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        report["entidades"].append(summary)

    national = args.output_root / "resumen_nacional"
    national.mkdir(parents=True, exist_ok=True)
    section.to_csv(national / "secciones_datos.csv", index=False)
    municipality.to_csv(national / "municipios_datos.csv", index=False)
    national_summary = {
        "entidad": "Resumen nacional",
        "secciones": int(len(section)),
        "municipios": int(len(municipality)),
        "entidades_federativas": len(entities),
    }
    (national / "resumen.json").write_text(
        json.dumps(national_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_root / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Paquetes generados: {len(entities)} entidades + resumen nacional")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
