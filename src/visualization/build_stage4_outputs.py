"""Build professional Matplotlib charts and territorial outputs."""

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
    "risk_score",
    "risk_level",
    "latest_abstention",
    "predicted_abstention",
    "trend_reliable",
    "risk_reason",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configure_matplotlib() -> None:
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


def save_figure(fig: plt.Figure, output_root: Path, name: str) -> list[str]:
    fig.tight_layout(pad=1.4)
    paths = [output_root / f"{name}.png", output_root / f"{name}.pdf"]
    for path in paths:
        fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return [str(path) for path in paths]


def load_scope(input_root: Path, scope: str) -> pd.DataFrame:
    data = pd.read_csv(input_root / f"ccpc_{scope}_integrated.csv", low_memory=False)
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


def build_semaforo(data: pd.DataFrame, output_path: Path) -> int:
    result = data[
        [
            "EDONOM",
            "MPIONOM",
            "SECCION",
            "TIPOSEC",
            "risk_score",
            "risk_level",
            "latest_abstention",
            "predicted_abstention",
            "trend_reliable",
            "prediction_available",
            "risk_reason",
            "display_zone",
        ]
    ].copy()
    result["semaforo"] = result["risk_level"].map(
        {"alto": "rojo", "medio": "amarillo", "bajo": "verde"}
    ).fillna("gris")
    result["consulta_status"] = result["risk_level"].map(
        {
            "alto": "prioridad de intervención",
            "medio": "monitoreo preventivo",
            "bajo": "seguimiento regular",
            "sin_historico": "sin histórico suficiente",
        }
    )
    result.sort_values(
        ["risk_score", "EDONOM", "MPIONOM"], ascending=[False, True, True], na_position="last"
    ).to_csv(output_path, index=False)
    return len(result)


def build_charts(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
    chart_paths = []
    reliable = data.loc[data["risk_score"].notna()].copy()
    counts = data["risk_level"].value_counts().reindex(
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
    chart_paths += save_figure(fig, output_root, f"{scope}_risk_distribution")

    top = reliable.nlargest(15, "risk_score").sort_values("risk_score")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top["display_zone"], top["risk_score"], color=COLORS["red"], height=0.68)
    ax.set_title(f"Top 15 zonas por índice de riesgo · {scope.title()}", loc="left")
    ax.set_xlabel("Índice de riesgo (0–100)")
    ax.set_xlim(0, 100)
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    chart_paths += save_figure(fig, output_root, f"{scope}_top_risk")

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
    chart_paths += save_figure(fig, output_root, f"{scope}_top_predicted_abstention")
    return chart_paths


def build_state_charts(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
    summary = (
        data.groupby("EDONOM", dropna=False)
        .agg(
            high_risk=("risk_level", lambda values: (values == "alto").sum()),
            mean_risk=("risk_score", "mean"),
            predicted_abstention=("predicted_abstention", "mean"),
        )
        .reindex(STATE_ORDER)
    )
    chart_paths = []
    for metric, title, xlabel, filename, color in [
        (
            "high_risk",
            f"Zonas de riesgo alto por entidad · {scope.title()}",
            "Número de zonas con riesgo alto",
            f"{scope}_states_high_risk",
            COLORS["red"],
        ),
        (
            "predicted_abstention",
            f"Abstención predicha promedio por entidad · {scope.title()}",
            "Abstención predicha promedio (%)",
            f"{scope}_states_predicted_abstention",
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
        chart_paths += save_figure(fig, output_root, filename)
    return chart_paths


def build_cdmx_charts(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
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
    chart_paths += save_figure(fig, output_root, f"{scope}_cdmx_latest_abstention")

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
        chart_paths += save_figure(
            fig, output_root, f"{scope}_cdmx_predicted_abstention"
        )
    return chart_paths


def build_cards(data: pd.DataFrame, output_root: Path, scope: str) -> int:
    cards = data.loc[data["risk_score"].notna()].nlargest(20, "risk_score").copy()
    cards[DISPLAY_COLUMNS].to_csv(output_root / f"{scope}_territorial_cards.csv", index=False)
    cards[DISPLAY_COLUMNS].to_json(
        output_root / f"{scope}_territorial_cards.json",
        orient="records",
        force_ascii=False,
        indent=2,
    )
    return len(cards)


def build_notebook(path: Path) -> None:
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
                "data = pd.read_csv(f'../outputs/integrated/ccpc_{scope}_integrated.csv', low_memory=False)\n",
                "data.head()",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "data['risk_level'].value_counts(dropna=False).reindex(['bajo','medio','alto','sin_historico'], fill_value=0).plot.bar(title='Distribución del riesgo')\n",
                "plt.xlabel('Nivel de riesgo'); plt.ylabel('Número de zonas'); plt.show()",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "data.loc[data.risk_score.notna()].nlargest(20, 'risk_score')[['EDONOM','MPIONOM','risk_score','risk_level','risk_reason']]",
            ],
        },
    ]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = project_root()
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "integrated")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "stage4")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    charts = []
    validation = {"project_area": "visualization_and_consultation", "scopes": {}}
    data_by_scope = {}
    for scope in ("section", "municipality"):
        data = load_scope(args.input_root, scope)
        data_by_scope[scope] = data
        semaforo_rows = build_semaforo(data, args.output_root / f"{scope}_semaforo.csv")
        charts += build_charts(data, args.output_root, scope)
        charts += build_state_charts(data, args.output_root, scope)
        charts += build_cdmx_charts(data, args.output_root, scope)
        cards = build_cards(data, args.output_root, scope)
        validation["scopes"][scope] = {
            "rows": int(len(data)),
            "semaforo_rows": semaforo_rows,
            "cards": cards,
            "duplicate_rows": int(data.duplicated(["EDOCVE", "MPIOCVE"] + (["SECCION", "TIPOSEC"] if scope == "section" else [])).sum()),
            "unreliable_rows": int((~data["trend_reliable"]).sum()),
            "risk_rows_with_score": int(data["risk_score"].notna().sum()),
            "prediction_rows": int(data["predicted_abstention"].notna().sum()),
        }
    notebook_dir = root / "notebooks"
    notebook_dir.mkdir(parents=True, exist_ok=True)
    build_notebook(notebook_dir / "04_exploracion_territorial.ipynb")
    validation["charts"] = charts
    validation["notebook"] = str(notebook_dir / "04_exploracion_territorial.ipynb")
    validation["checks"] = [
        "Los duplicados territoriales deben ser cero.",
        "Las zonas sin histórico conservan nivel sin_historico.",
        "La abstención predicha se etiqueta como predicción, no como observación.",
    ]
    (args.output_root / "stage4_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Stage 4: {len(charts)} gráficos Matplotlib y fichas generados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
