"""Visualizaciones de la Simulación 2: comparación SIN vs CON intervención.

Lee los CSV generados por 07_simular_escenario_intervencion.py y produce
(PNG + PDF) por alcance (municipios / secciones):

  01_abstencionPorPerfil       abstención media 2030 sin vs con intervención, por perfil
  02_distribucionNiveles       zonas en nivel alto/medio/bajo, antes y después
  03_distribucionAbstencion    histograma superpuesto de la abstención proyectada
  04_baseVsIntervencion        dispersión zona a zona (bajo la diagonal = mejora)
  05_topZonasAntesDespues      las 10 zonas de mayor abstención, antes y después
  06_reduccionPorEntidad       (sólo nacional) reducción media por entidad
  07_sensibilidad              (sólo nacional, municipios) conservador/base/optimista

Salida:
  outputs/visualizaciones/intervencion/<alcance>/                         (nacional)
  outputs/entidades/<entidad>/visualizaciones/intervencion/<alcance>/     (por entidad)
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import PercentFormatter
except ImportError:
    sys.exit("ERROR: matplotlib no está instalado (pip install matplotlib)")

C_BASE, C_INT = "#c9351e", "#257e4e"
C_NIVEL = {"alto": "#c9351e", "medio": "#c47d10", "bajo": "#257e4e"}
C_PERFIL = {"A": "#c9351e", "B": "#c47d10", "C": "#3b6fb6", "sin_perfil": "#8c867b"}
NOMBRE_PERFIL = {"A": "A · base crítica", "B": "B · deterioro", "C": "C · inestable", "sin_perfil": "Sin perfil"}
ETQ = {"base": "Sin intervención", "int": "Con intervención"}
MAX_PUNTOS = 6000


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _slug(texto: str) -> str:
    return texto.lower().replace(" ", "_")


def _guardar(fig, base: Path) -> None:
    """PNG + PDF atómicos. `base` va sin extensión."""
    base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        tmp = base.parent / f"{base.name}.{ext}.tmp"
        fig.savefig(tmp, format=ext, dpi=150, bbox_inches="tight", facecolor="white")
        tmp.replace(base.parent / f"{base.name}.{ext}")
    plt.close(fig)


def _estilo(ax, titulo, xlabel="", ylabel=""):
    ax.set_title(titulo, fontsize=12, fontweight="bold", pad=14)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.tick_params(axis="both", labelsize=8)


def _disp(df: pd.DataFrame) -> pd.DataFrame:
    if "abstencion_proyectada_intervencion" not in df.columns:
        return df.iloc[0:0]
    return df.dropna(subset=["abstencion_proyectada", "abstencion_proyectada_intervencion"]).copy()


def _etiqueta(r, alcance, entidad):
    if entidad == "CIUDAD DE MEXICO" and hasattr(r, "ALCALDIA"):
        nombre = str(getattr(r, "ALCALDIA", "")).strip()
    else:
        nombre = str(getattr(r, "MPIONOM", "")).strip()
    if alcance == "secciones" and hasattr(r, "SECCION"):
        return f"{nombre[:24]} · secc. {int(r.SECCION)}"
    return nombre[:34]


# ------------------------------------------------------------------ gráficas
def g1_por_perfil(df, out, alcance, entidad):
    d = _disp(df)
    perfiles = [p for p in ["A", "B", "C", "sin_perfil"] if (d["perfil_intervencion"] == p).any()]
    if not perfiles:
        return
    base = [d.loc[d["perfil_intervencion"] == p, "abstencion_proyectada"].mean() * 100 for p in perfiles]
    new = [d.loc[d["perfil_intervencion"] == p, "abstencion_proyectada_intervencion"].mean() * 100 for p in perfiles]
    n = [int((d["perfil_intervencion"] == p).sum()) for p in perfiles]
    x = np.arange(len(perfiles))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    b1 = ax.bar(x - 0.2, base, 0.4, color=C_BASE, label=ETQ["base"])
    b2 = ax.bar(x + 0.2, new, 0.4, color=C_INT, label=ETQ["int"])
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{b.get_height():.1f}%",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{NOMBRE_PERFIL[p]}\n(n={k:,})" for p, k in zip(perfiles, n)], fontsize=8)
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_ylim(0, max(base + new) * 1.18)
    ax.legend(fontsize=8, ncol=2, loc="upper center")
    _estilo(ax, f"01 Abstención proyectada 2030 por perfil - {alcance.capitalize()}", "", "Abstención media")
    fig.tight_layout()
    _guardar(fig, out / "01_abstencionPorPerfil")


def g2_niveles(df, out, alcance, entidad):
    d = _disp(df)
    if d.empty:
        return
    niveles = ["alto", "medio", "bajo"]
    base = [int((d["nivel_base_ref"] == n).sum()) for n in niveles]
    new = [int((d["nivel_escenario_intervencion"] == n).sum()) for n in niveles]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    b1 = ax.bar(x - 0.2, base, 0.4, color=[C_NIVEL[n] for n in niveles], alpha=0.45, edgecolor=C_BASE, hatch="//", label=ETQ["base"])
    b2 = ax.bar(x + 0.2, new, 0.4, color=[C_NIVEL[n] for n in niveles], edgecolor="white", label=ETQ["int"])
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{int(b.get_height()):,}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([n.capitalize() for n in niveles])
    ax.set_ylim(0, max(base + new) * 1.18)
    ax.legend(handles=[Patch(facecolor="#bbbbbb", hatch="//", edgecolor="#777", label=ETQ["base"]),
                       Patch(facecolor="#777777", label=ETQ["int"])], fontsize=8, ncol=2, loc="upper center")
    _estilo(ax, f"02 Zonas por nivel de riesgo 2030 - {alcance.capitalize()}", "Nivel (cortes del escenario base)", "Número de zonas")
    fig.tight_layout()
    _guardar(fig, out / "02_distribucionNiveles")


def g3_histograma(df, out, alcance, entidad):
    d = _disp(df)
    if d.empty:
        return
    bins = np.linspace(0, 1, 41)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(d["abstencion_proyectada"], bins=bins, color=C_BASE, alpha=0.55, label=ETQ["base"])
    ax.hist(d["abstencion_proyectada_intervencion"], bins=bins, color=C_INT, alpha=0.55, label=ETQ["int"])
    ax.axvline(d["abstencion_proyectada"].mean(), color=C_BASE, ls="--", lw=1.2)
    ax.axvline(d["abstencion_proyectada_intervencion"].mean(), color=C_INT, ls="--", lw=1.2)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.legend(fontsize=8)
    _estilo(ax, f"03 Distribución de la abstención proyectada - {alcance.capitalize()}", "Abstención proyectada 2030", "Número de zonas")
    fig.tight_layout()
    _guardar(fig, out / "03_distribucionAbstencion")


def g4_dispersion(df, out, alcance, entidad):
    d = _disp(df)
    if d.empty:
        return
    if len(d) > MAX_PUNTOS:
        d = d.sample(MAX_PUNTOS, random_state=0)
    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.plot([0, 1], [0, 1], color="#555", lw=1, ls="--", label="Sin cambio")
    for p in ["sin_perfil", "C", "B", "A"]:
        s = d[d["perfil_intervencion"] == p]
        if not s.empty:
            ax.scatter(s["abstencion_proyectada"], s["abstencion_proyectada_intervencion"], s=12, alpha=0.55,
                       color=C_PERFIL[p], label=NOMBRE_PERFIL[p])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.legend(fontsize=8, loc="upper left")
    _estilo(ax, f"04 Sin vs con intervención, zona a zona - {alcance.capitalize()}",
            "Abstención sin intervención", "Abstención con intervención")
    fig.tight_layout()
    _guardar(fig, out / "04_baseVsIntervencion")


def g5_top_zonas(df, out, alcance, entidad):
    d = _disp(df).nlargest(10, "abstencion_proyectada")
    if d.empty:
        return
    etq = [_etiqueta(r, alcance, entidad) for r in d.itertuples()]
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(y - 0.2, d["abstencion_proyectada"] * 100, 0.4, color=C_BASE, label=ETQ["base"])
    ax.barh(y + 0.2, d["abstencion_proyectada_intervencion"] * 100, 0.4, color=C_INT, label=ETQ["int"])
    ax.set_yticks(y)
    ax.set_yticklabels(etq, fontsize=8)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    _estilo(ax, f"05 Las 10 zonas de mayor abstención: antes y después - {alcance.capitalize()}", "Abstención proyectada 2030", "")
    ax.set_title(ax.get_title(), fontsize=12, fontweight="bold", pad=34)
    ax.legend(fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
    n_sat = int((d["abstencion_proyectada"] >= 0.995).sum())
    if n_sat:
        fig.text(0.01, -0.03, f"Nota: {n_sat} de estas zonas tienen proyección saturada en 100 % "
                 "(extrapolación lineal truncada en 0-1); interpretar con cautela.", fontsize=7, color="#666")
    fig.tight_layout()
    _guardar(fig, out / "05_topZonasAntesDespues")


def g6_por_entidad(df, out, alcance):
    d = _disp(df)
    if d.empty or "EDONOM" not in d.columns:
        return
    g = d.groupby("EDONOM").agg(red=("reduccion_abstencion_pp", "mean"), n=("reduccion_abstencion_pp", "size"),
                                interv=("propuestas_aplicadas", lambda x: int((x != "ninguna").sum()))).sort_values("red")
    fig, ax = plt.subplots(figsize=(10, max(5, 0.28 * len(g))))
    ax.barh(g.index, g["red"].values, color=C_INT)
    for i, (v, n, k) in enumerate(zip(g["red"], g["n"], g["interv"])):
        ax.text(v, i, f" {v:.2f} pp  ·  {k / n:.0%} de zonas intervenidas", va="center", fontsize=7)
    ax.set_xlim(0, max(g["red"].max(), 0.1) * 1.65)
    _estilo(ax, f"06 Reducción media por entidad (todas las zonas con proyección) - {alcance.capitalize()}",
            "Reducción media (pp)", "")
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    _guardar(fig, out / "06_reduccionPorEntidad")


def g7_sensibilidad(sens: pd.DataFrame, out):
    if sens is None or sens.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colores = [C_NIVEL["medio"], C_INT, "#1b5e3b"][: len(sens)]
    bars = ax.bar(sens["escenario"], sens["reduccion_media_pp"], color=colores)
    for b, s in zip(bars, sens["salen_de_alto"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{b.get_height():.2f} pp\n{int(s):,} salen de 'alto'", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, sens["reduccion_media_pp"].max() * 1.3)
    _estilo(ax, "07 Sensibilidad: reducción según supuesto de efectividad (municipios)", "Escenario", "Reducción media (pp)")
    fig.tight_layout()
    _guardar(fig, out / "07_sensibilidad")


GRAFICAS = [g1_por_perfil, g2_niveles, g3_histograma, g4_dispersion, g5_top_zonas]


def generar(df: pd.DataFrame, out: Path, alcance: str, nacional: bool, entidad: str = "Nacional", sens=None) -> None:
    for g in GRAFICAS:
        g(df, out, alcance, entidad)
    if nacional:
        g6_por_entidad(df, out, alcance)
        if alcance == "municipios":
            g7_sensibilidad(sens, out)


def main() -> None:
    raiz = _project_root()
    ap = argparse.ArgumentParser(description="Visualizaciones sin vs con intervención")
    ap.add_argument("--escenarios-dir", type=Path, default=raiz / "outputs" / "escenarios")
    ap.add_argument("--nacional-dir", type=Path, default=raiz / "outputs" / "visualizaciones" / "intervencion")
    ap.add_argument("--entidades-dir", type=Path, default=raiz / "outputs" / "entidades")
    ap.add_argument("--entidad", type=str, default=None, help="Sólo una entidad (filtro por nombre)")
    ap.add_argument("--solo-nacional", action="store_true", help="No generar gráficas por entidad")
    args = ap.parse_args()

    archivos = {
        "municipios": args.escenarios_dir / "ccpc_municipioEscenarioConIntervencion.csv",
        "secciones": args.escenarios_dir / "ccpc_seccionEscenarioConIntervencion.csv",
    }
    sens_csv = args.escenarios_dir / "ccpc_sensibilidadIntervencion.csv"
    sens = pd.read_csv(sens_csv, encoding="utf-8") if sens_csv.exists() else None

    datos = {a: pd.read_csv(p, encoding="utf-8") for a, p in archivos.items() if p.exists()}
    if not datos:
        sys.exit("No se encontraron CSV con intervención. Corre primero 07_simular_escenario_intervencion.py")

    for alcance, df in datos.items():
        print(f"Nacional - {alcance}...")
        generar(df, args.nacional_dir / alcance, alcance, True, "Nacional", sens)

    if not args.solo_nacional:
        entidades = sorted({e for df in datos.values() for e in df["EDONOM"].dropna().unique()})
        if args.entidad:
            entidades = [e for e in entidades if args.entidad.lower() in e.lower()]
        for ent in entidades:
            print(f"Entidad: {ent}")
            for alcance, df in datos.items():
                sub = df[df["EDONOM"] == ent]
                if not sub.empty:
                    generar(sub, args.entidades_dir / _slug(ent) / "visualizaciones" / "intervencion" / alcance,
                            alcance, False)
    print(f"\nListo. Nacional en: {args.nacional_dir}")


if __name__ == "__main__":
    main()

