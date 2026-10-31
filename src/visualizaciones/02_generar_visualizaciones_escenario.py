"""Generar visualizaciones de escenario - Fase 4.

Genera 7 gráficas por entidad federativa y alcance (municipios/secciones):
1. Resumen territorial        5. Matriz transición de riesgo
2. Top abstención proyectada  6. Perfil histórico
3. Mayor deterioro esperado   7. Cobertura y calidad
4. Tendencia vs abstención

Salida: PNG + PDF en outputs/entidades/<entidad>/visualizaciones/{secciones,municipios}/
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
except ImportError:
    sys.exit("ERROR: matplotlib no está instalado (pip install matplotlib)")

COLORES = {"alto": "#c9351e", "medio": "#c47d10", "bajo": "#257e4e", "sin_historico": "#8c867b"}
NIVELES = ["alto", "medio", "bajo"]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_fig(fig, base: Path) -> None:
    """Guarda PNG y PDF de forma atómica. `base` va sin extensión."""
    base.parent.mkdir(parents=True, exist_ok=True)
    tmp_png = base.parent / (base.name + ".png.tmp")
    tmp_pdf = base.parent / (base.name + ".pdf.tmp")
    fig.savefig(tmp_png, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    fig.savefig(tmp_pdf, format="pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    tmp_png.replace(base.parent / (base.name + ".png"))
    tmp_pdf.replace(base.parent / (base.name + ".pdf"))


def _style_axes(ax, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, fontsize=12, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.tick_params(axis="both", labelsize=8)


def _disponibles(df: pd.DataFrame) -> pd.DataFrame:
    if "proyeccion_disponible" not in df.columns:
        return df.iloc[0:0]
    mask = df["proyeccion_disponible"].fillna(False).astype(bool)
    return df[mask].copy()


def _etiqueta(row, scope: str) -> str:
    """Etiqueta de zona: municipio, o municipio + sección si el alcance es secciones."""
    nombre = str(getattr(row, "MPIONOM", ""))[:15]
    if scope == "secciones" and hasattr(row, "SECCION"):
        return f"{nombre} {row.SECCION}"
    return nombre


def _g1_resumen(df, out_dir, scope):
    counts = df["nivel_escenario"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(counts.index, counts.values, color=[COLORES.get(c, "#8c867b") for c in counts.index], edgecolor="white")
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(val),
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    _style_axes(ax, f"01 Resumen territorial - {scope.capitalize()}", "Nivel de escenario", "Número de zonas")
    fig.tight_layout()
    _save_fig(fig, out_dir / "01_resumenTerritorial")


def _g2_top_abstencion(df, out_dir, scope):
    top = _disponibles(df).nlargest(10, "abstencion_proyectada")
    if top.empty:
        return
    labels = [_etiqueta(r, scope) for r in top.itertuples()]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, top["abstencion_proyectada"] * 100, color=COLORES["alto"], edgecolor="white")
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    _style_axes(ax, f"02 Top abstención proyectada - {scope.capitalize()}",
                "Abstención proyectada 2030 (%)", "Zona")
    fig.tight_layout()
    _save_fig(fig, out_dir / "02_topAbstencionProyectada")


def _g3_deterioro(df, out_dir, scope):
    top = _disponibles(df).nlargest(10, "cambio_abstencion_vs_base")
    if top.empty:
        return
    labels = [_etiqueta(r, scope) for r in top.itertuples()]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, top["cambio_abstencion_vs_base"] * 100, color=COLORES["medio"], edgecolor="white")
    ax.invert_yaxis()
    _style_axes(ax, f"03 Mayor deterioro esperado - {scope.capitalize()}",
                "Cambio vs año base (pp)", "Zona")
    fig.tight_layout()
    _save_fig(fig, out_dir / "03_mayorDeterioroEsperado")


def _g4_tendencia(df, out_dir, scope):
    d = _disponibles(df)
    if d.empty or "participation_slope" not in d.columns:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for nivel in NIVELES:
        sub = d[d["nivel_escenario"] == nivel]
        if not sub.empty:
            ax.scatter(sub["participation_slope"] * 100, sub["abstencion_proyectada"] * 100,
                       color=COLORES[nivel], label=nivel.capitalize(), alpha=0.6, s=20)
    _style_axes(ax, f"04 Tendencia vs abstención - {scope.capitalize()}",
                "Pendiente de participación (pp/año)", "Abstención proyectada (%)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save_fig(fig, out_dir / "04_tendenciaVsAbstencion")


def _g5_matriz(df, out_dir, scope):
    d = _disponibles(df)
    if d.empty or "risk_level" not in d.columns:
        return
    d["cambio_direccion"] = d["cambio_abstencion_vs_base"].apply(lambda x: "Aumenta" if x > 0 else "Disminuye")
    pivot = pd.crosstab(d["risk_level"], d["cambio_direccion"])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, fontsize=8)
    ax.set_yticklabels(pivot.index, fontsize=8)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            ax.text(j, i, str(pivot.values[i, j]), ha="center", va="center", fontsize=9, fontweight="bold")
    _style_axes(ax, f"05 Matriz transición de riesgo - {scope.capitalize()}",
                "Cambio en abstención", "Nivel de riesgo base")
    ax.grid(False)
    fig.tight_layout()
    _save_fig(fig, out_dir / "05_matrizTransicionRiesgo")


def _g6_perfil(df, out_dir, scope):
    d = _disponibles(df)
    if d.empty:
        return
    niveles = ["bajo", "medio", "alto"]
    data = [d.loc[d["nivel_escenario"] == n, "abstencion_proyectada"].dropna().values * 100 for n in niveles]
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(data, patch_artist=True)
    ax.set_xticklabels(niveles)
    for patch, nivel in zip(bp["boxes"], niveles):
        patch.set_facecolor(COLORES[nivel])
        patch.set_alpha(0.7)
    _style_axes(ax, f"06 Perfil histórico - {scope.capitalize()}",
                "Nivel de escenario 2030", "Abstención proyectada (%)")
    fig.tight_layout()
    _save_fig(fig, out_dir / "06_perfilHistorico")


def _g7_cobertura(df, out_dir, scope):
    d = _disponibles(df)
    if d.empty or not {"years_observed", "risk_score"} <= set(d.columns):
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for nivel in NIVELES:
        sub = d[d["nivel_escenario"] == nivel]
        if not sub.empty:
            ax.scatter(sub["years_observed"], sub["risk_score"],
                       color=COLORES[nivel], label=nivel.capitalize(), alpha=0.6, s=20)
    _style_axes(ax, f"07 Cobertura y calidad - {scope.capitalize()}",
                "Años observados", "Puntaje de riesgo")
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save_fig(fig, out_dir / "07_coberturaYCalidad")


GRAFICAS = [_g1_resumen, _g2_top_abstencion, _g3_deterioro, _g4_tendencia,
            _g5_matriz, _g6_perfil, _g7_cobertura]


def generar_visualizaciones(df: pd.DataFrame, entidad_dir: Path, scope: str) -> None:
    """Genera las 7 gráficas de un alcance (municipios/secciones) de una entidad."""
    out_dir = _ensure_dir(entidad_dir / "visualizaciones" / scope)
    for grafica in GRAFICAS:
        grafica(df, out_dir, scope)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generar visualizaciones de escenario por entidad")
    parser.add_argument("--escenarios-dir", type=Path, default=_project_root() / "outputs" / "escenarios")
    parser.add_argument("--output-dir", type=Path, default=_project_root() / "outputs" / "entidades")
    parser.add_argument("--entidad", type=str, default=None, help="Filtrar por nombre de entidad")
    args = parser.parse_args()

    mun_csv = args.escenarios_dir / "ccpc_municipioEscenarioSinIntervencion.csv"
    sec_csv = args.escenarios_dir / "ccpc_seccionEscenarioSinIntervencion.csv"
    df_mun = pd.read_csv(mun_csv) if mun_csv.exists() else pd.DataFrame()
    df_sec = pd.read_csv(sec_csv) if sec_csv.exists() else pd.DataFrame()

    entidades = set()
    for df in (df_mun, df_sec):
        if not df.empty:
            entidades.update(df["EDONOM"].dropna().unique())
    entidades = sorted(entidades)

    if args.entidad:
        entidades = [e for e in entidades if args.entidad.lower() in e.lower()]

    for entidad in entidades:
        print(f"\nGenerando visualizaciones para {entidad}...")
        entidad_dir = _ensure_dir(args.output_dir / entidad.lower().replace(" ", "_"))
        for scope, df in (("municipios", df_mun), ("secciones", df_sec)):
            if df.empty:
                continue
            sub = df[df["EDONOM"] == entidad].copy()
            if not sub.empty:
                generar_visualizaciones(sub, entidad_dir, scope)
        print(f"  Guardadas en: {entidad_dir / 'visualizaciones'}")


if __name__ == "__main__":
    main()