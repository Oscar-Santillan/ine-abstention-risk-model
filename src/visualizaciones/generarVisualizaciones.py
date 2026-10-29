"""Genera visualizaciones profesionales y salidas territoriales reproducibles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd


COLORS = {
    "navy": "#17324D",
    "blue": "#2F6B9A",
    "red": "#C84B4B",
    "amber": "#D99A2B",
    "green": "#4E8B57",
    "gray": "#8996A3",
    "light": "#EEF2F5",
    "cdmx": "#7B4FA3",
}
RISK_COLORS = {
    "bajo": COLORS["green"],
    "medio": COLORS["amber"],
    "alto": COLORS["red"],
    "sin_historico": COLORS["gray"],
}
STATE_ORDER = [
    "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CAMPECHE",
    "CHIAPAS", "CHIHUAHUA", "CIUDAD DE MEXICO", "COAHUILA", "COLIMA",
    "DURANGO", "GUANAJUATO", "GUERRERO", "HIDALGO", "JALISCO", "MEXICO",
    "MICHOACAN", "MORELOS", "NAYARIT", "NUEVO LEON", "OAXACA", "PUEBLA",
    "QUERETARO", "QUINTANA ROO", "SAN LUIS POTOSI", "SINALOA", "SONORA",
    "TABASCO", "TAMAULIPAS", "TLAXCALA", "VERACRUZ", "YUCATAN", "ZACATECAS",
]

DISPLAY_COLUMNS = [
    "EDONOM",
    "MPIONOM",
    "SECCION",
    "indiceRiesgo_score",
    "indiceRiesgo_level",
    "latest_abstention",
    "predicted_abstention",
    "trend_reliable",
    "indiceRiesgo_reason",
]


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def configurarMatplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelcolor": COLORS["navy"],
            "axes.edgecolor": "#D7DEE5",
            "axes.linewidth": 0.8,
            "xtick.color": "#52616F",
            "ytick.color": "#52616F",
            "grid.color": "#DCE3E9",
            "grid.linewidth": 0.8,
            "grid.alpha": 0.8,
        }
    )


def guardarFigura(fig: plt.Figure, output_root: Path, name: str) -> list[str]:
    fig.tight_layout(pad=1.4)
    paths = [output_root / f"{name}.png", output_root / f"{name}.pdf"]
    for path in paths:
        fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return [str(path) for path in paths]


def cargarAlcance(input_root: Path, scope: str) -> pd.DataFrame:
    data = pd.read_csv(input_root / f"ccpc_{'seccion' if scope == 'section' else 'municipio'}ResultadosIntegrados.csv", low_memory=False)
    if scope == "municipality":
        data["SECCION"] = pd.NA
        data["TIPOSEC"] = pd.NA
    data["display_zone"] = data["MPIONOM"]
    data.loc[data["SECCION"].notna(), "display_zone"] = (
        data.loc[data["SECCION"].notna(), "MPIONOM"]
        + " · sección "
        + data.loc[data["SECCION"].notna(), "SECCION"].astype(str)
    )
    return data


def construirSemaforo(data: pd.DataFrame, output_path: Path) -> int:
    result = data[
        [
            "EDONOM",
            "MPIONOM",
            "SECCION",
            "TIPOSEC",
            "indiceRiesgo_score",
            "indiceRiesgo_level",
            "latest_abstention",
            "predicted_abstention",
            "trend_reliable",
            "prediction_available",
            "indiceRiesgo_reason",
            "display_zone",
        ]
    ].copy()
    result["semaforo"] = result["indiceRiesgo_level"].map(
        {"alto": "rojo", "medio": "amarillo", "bajo": "verde"}
    ).fillna("gris")
    result["consulta_status"] = result["indiceRiesgo_level"].map(
        {
            "alto": "prioridad de intervención",
            "medio": "monitoreo preventivo",
            "bajo": "seguimiento regular",
            "sin_historico": "sin histórico suficiente",
        }
    )
    result.sort_values(
        ["indiceRiesgo_score", "EDONOM", "MPIONOM"], ascending=[False, True, True], na_position="last"
    ).to_csv(output_path, index=False)
    return len(result)


def construirGraficas(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
    chart_paths = []
    reliable = data.loc[data["indiceRiesgo_score"].notna()].copy()
    counts = data["indiceRiesgo_level"].value_counts().reindex(
        ["bajo", "medio", "alto", "sin_historico"], fill_value=0
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(
        ["Bajo", "Medio", "Alto", "Sin histórico"],
        counts.values,
        color=[RISK_COLORS[level] for level in counts.index],
        width=0.68,
    )
    ax.set_title(f"Semáforo territorial · {scope.title()}", loc="left")
    ax.set_xlabel("Nivel de riesgo")
    ax.set_ylabel("Número de zonas")
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.bar_label(bars, labels=[f"{value:,}" for value in counts.values], padding=5)
    chart_paths += guardarFigura(fig, output_root, f"{scope}_indiceRiesgo_distribution")

    top = reliable.nlargest(15, "indiceRiesgo_score").sort_values("indiceRiesgo_score")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top["display_zone"], top["indiceRiesgo_score"], color=COLORS["red"], height=0.68)
    ax.set_title(f"Top 15 zonas por índice de riesgo · {scope.title()}", loc="left")
    ax.set_xlabel("Índice de riesgo (0–100)")
    ax.set_xlim(0, 100)
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    chart_paths += guardarFigura(fig, output_root, f"{scope}_top_indiceRiesgo")

    predicted = data.loc[data["predicted_abstention"].notna()].nlargest(
        15, "predicted_abstention"
    ).sort_values("predicted_abstention")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(
        predicted["display_zone"],
        predicted["predicted_abstention"].mul(100),
        color=COLORS["blue"],
        height=0.68,
    )
    ax.set_title(f"Top 15 zonas por abstención predicha · {scope.title()}", loc="left")
    ax.set_xlabel("Abstención predicha (%)")
    ax.xaxis.set_major_formatter(PercentFormatter(100))
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    chart_paths += guardarFigura(fig, output_root, f"{scope}_top_abstencionPredicha")
    return chart_paths


def construirGraficasEntidades(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
    summary = (
        data.groupby("EDONOM", dropna=False)
        .agg(
            high_indiceRiesgo=("indiceRiesgo_level", lambda values: (values == "alto").sum()),
            mean_indiceRiesgo=("indiceRiesgo_score", "mean"),
            predicted_abstention=("predicted_abstention", "mean"),
        )
        .reindex(STATE_ORDER)
    )
    chart_paths = []
    for metric, title, xlabel, filename, color in [
        (
            "high_indiceRiesgo",
            f"Zonas de riesgo alto por entidad · {scope.title()}",
            "Número de zonas con riesgo alto",
            f"{scope}_states_high_indiceRiesgo",
            COLORS["red"],
        ),
        (
            "predicted_abstention",
            f"Abstención predicha promedio por entidad · {scope.title()}",
            "Abstención predicha promedio (%)",
            f"{scope}_states_abstencionPredicha",
            COLORS["blue"],
        ),
    ]:
        values = summary[metric].fillna(0).sort_values()
        fig, ax = plt.subplots(figsize=(10, 10))
        bars = ax.barh(
            values.index,
            values.values * (100 if metric == "predicted_abstention" else 1),
            color=color,
        )
        if "CIUDAD DE MEXICO" in values.index:
            bars[values.index.tolist().index("CIUDAD DE MEXICO")].set_color(
                COLORS["cdmx"]
            )
        ax.set_title(title, loc="left")
        ax.set_xlabel(xlabel)
        if metric == "predicted_abstention":
            ax.xaxis.set_major_formatter(PercentFormatter(100))
        ax.grid(axis="x")
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", labelsize=8, length=0)
        chart_paths += guardarFigura(fig, output_root, filename)
    return chart_paths


def construirGraficasCiudadMexico(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
    cdmx = data.loc[data["EDONOM"].eq("CIUDAD DE MEXICO")].copy()
    if cdmx.empty:
        return []
    chart_paths = []
    top = cdmx.nlargest(15, "latest_abstention").sort_values("latest_abstention")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(
        top["display_zone"],
        top["latest_abstention"].mul(100),
        color=COLORS["cdmx"],
        height=0.68,
    )
    ax.set_title(
        f"CDMX · Top 15 zonas por abstención observada · {scope.title()}",
        loc="left",
    )
    ax.set_xlabel("Abstención observada más reciente (%)")
    ax.xaxis.set_major_formatter(PercentFormatter(100))
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    chart_paths += guardarFigura(fig, output_root, f"{scope}_cdmx_abstencionReciente")

    predicted = cdmx.loc[cdmx["predicted_abstention"].notna()].nlargest(
        15, "predicted_abstention"
    ).sort_values("predicted_abstention")
    if not predicted.empty:
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(
            predicted["display_zone"],
            predicted["predicted_abstention"].mul(100),
            color=COLORS["blue"],
            height=0.68,
        )
        ax.set_title(
            f"CDMX · Top 15 zonas por abstención predicha · {scope.title()}",
            loc="left",
        )
        ax.set_xlabel("Abstención predicha (%)")
        ax.xaxis.set_major_formatter(PercentFormatter(100))
        ax.grid(axis="x")
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        chart_paths += guardarFigura(
            fig, output_root, f"{scope}_cdmx_abstencionPredicha"
        )
    return chart_paths


def construirFichas(data: pd.DataFrame, output_root: Path, scope: str) -> int:
    cards = data.loc[data["indiceRiesgo_score"].notna()].nlargest(20, "indiceRiesgo_score").copy()
    cards[DISPLAY_COLUMNS].to_csv(output_root / f"{scope}_fichasTerritoriales.csv", index=False)
    cards[DISPLAY_COLUMNS].to_json(
        output_root / f"{scope}_fichasTerritoriales.json",
        orient="records",
        force_ascii=False,
        indent=2,
    )
    return len(cards)


def construirCuaderno(path: Path) -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Etapa 4 · Exploración territorial\n",
                "Consulta rankings, semáforo y predicciones. Las zonas `sin_historico` no se interpretan como riesgo confiable.",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "scope = 'municipality'\n",
                "data = pd.read_csv('../outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv', low_memory=False)\n",
                "data.head()",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "data['indiceRiesgo_level'].value_counts(dropna=False).reindex(['bajo','medio','alto','sin_historico'], fill_value=0).plot.bar(title='Distribución del riesgo')\n",
                "plt.xlabel('Nivel de riesgo'); plt.ylabel('Número de zonas'); plt.show()",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "data.loc[data.indiceRiesgo_score.notna()].nlargest(20, 'indiceRiesgo_score')[['EDONOM','MPIONOM','indiceRiesgo_score','indiceRiesgo_level','indiceRiesgo_reason']]",
            ],
        },
    ]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = obtenerRaizProyecto()
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "resultadosIntegrados")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "visualizaciones")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    configurarMatplotlib()
    charts = []
    validation = {"project_area": "visualizaciones_and_consultation", "scopes": {}}
    data_by_scope = {}
    for scope in ("section", "municipality"):
        data = cargarAlcance(args.input_root, scope)
        data_by_scope[scope] = data
        semaforo_rows = construirSemaforo(data, args.output_root / f"{'secciones' if scope == 'section' else 'municipios'}_semaforo.csv")
        charts += construirGraficas(data, args.output_root, scope)
        charts += construirGraficasEntidades(data, args.output_root, scope)
        charts += construirGraficasCiudadMexico(data, args.output_root, scope)
        cards = construirFichas(data, args.output_root, scope)
        validation["scopes"][scope] = {
            "rows": int(len(data)),
            "semaforo_rows": semaforo_rows,
            "cards": cards,
            "duplicate_rows": int(data.duplicated(["EDOCVE", "MPIOCVE"] + (["SECCION", "TIPOSEC"] if scope == "section" else [])).sum()),
            "unreliable_rows": int((~data["trend_reliable"]).sum()),
            "indiceRiesgo_rows_with_score": int(data["indiceRiesgo_score"].notna().sum()),
            "prediction_rows": int(data["predicted_abstention"].notna().sum()),
        }
    notebook_dir = root / "notebooks"
    notebook_dir.mkdir(parents=True, exist_ok=True)
    construirCuaderno(notebook_dir / "exploracionTerritorial.ipynb")
    validation["charts"] = charts
    validation["notebook"] = str(notebook_dir / "exploracionTerritorial.ipynb")
    validation["checks"] = [
        "Los duplicados territoriales deben ser cero.",
        "Las zonas sin histórico conservan nivel sin_historico.",
        "La abstención predicha se etiqueta como predicción, no como observación.",
    ]
    (args.output_root / "visualizaciones_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Stage 4: {len(charts)} gráficos Matplotlib y fichas generados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
