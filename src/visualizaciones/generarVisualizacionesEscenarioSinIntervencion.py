"""Genera gráficas profesionales para el escenario sin intervención."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter


COLORES_NIVEL = {"bajo": "#2a9d8f", "medio": "#e9c46a", "alto": "#e76f51"}


def configurarEstilo() -> None:
    """Configura una estética sobria y legible para las gráficas."""

    plt.rcParams.update(
        {
            "figure.dpi": 180,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlepad": 14,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#d9dee3",
            "grid.linewidth": 0.7,
        }
    )


def guardar(figura: plt.Figure, ruta: Path) -> None:
    """Guarda una figura en PNG y PDF."""

    ruta.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(ruta.with_suffix(".png"), bbox_inches="tight", facecolor="white")
    figura.savefig(ruta.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(figura)


def graficaDistribucion(datos: pd.DataFrame, alcance: str, salida: Path) -> None:
    """Muestra la distribución de niveles del escenario."""

    conteo = (
        datos["nivel_escenario"]
        .value_counts()
        .reindex(["bajo", "medio", "alto", "sin_historico"], fill_value=0)
    )
    figura, eje = plt.subplots(figsize=(9, 5.2))
    barras = eje.bar(
        conteo.index.str.replace("_", " ").str.title(),
        conteo.values,
        color=["#2a9d8f", "#e9c46a", "#e76f51", "#9aa5b1"],
    )
    eje.set_title(f"Escenario sin intervención por {alcance}")
    eje.set_ylabel("Número de zonas")
    eje.set_xlabel("Nivel proyectado de abstención")
    eje.bar_label(barras, fmt="{:,.0f}")
    eje.text(
        0,
        -0.22,
        "Fuente: CCPC 2009–2024 · proyección inercial al ciclo 2030",
        transform=eje.transAxes,
        fontsize=8,
        color="#586069",
    )
    guardar(figura, salida / f"distribucionEscenario_{alcance}")


def graficaComparacion(datos: pd.DataFrame, alcance: str, salida: Path) -> None:
    """Compara abstención base y abstención proyectada."""

    confiables = datos[datos["proyeccion_disponible"]].copy()
    resumen = pd.DataFrame(
        {
            "Abstención observada 2024": confiables["latest_abstention"].mean(),
            "Abstención proyectada 2030": confiables["abstencion_proyectada"].mean(),
        },
        index=["Promedio nacional"],
    )
    figura, eje = plt.subplots(figsize=(8, 5.2))
    barras = eje.bar(
        resumen.columns,
        resumen.iloc[0],
        color=["#457b9d", "#e76f51"],
        width=0.55,
    )
    eje.yaxis.set_major_formatter(PercentFormatter(1))
    eje.set_ylim(0, max(resumen.iloc[0]) * 1.25)
    eje.set_ylabel("Abstención (%)")
    eje.set_xlabel("Referencia temporal")
    eje.set_title(f"Cambio promedio de abstención · {alcance}")
    eje.bar_label(barras, fmt=lambda valor: f"{valor:.1%}")
    eje.text(
        0,
        -0.22,
        "Fuente: CCPC 2009–2024 · sólo zonas con proyección disponible",
        transform=eje.transAxes,
        fontsize=8,
        color="#586069",
    )
    guardar(figura, salida / f"comparacionAbstencion_{alcance}")


def graficaTop(datos: pd.DataFrame, alcance: str, salida: Path) -> None:
    """Presenta las zonas con mayor abstención proyectada."""

    top = (
        datos[datos["proyeccion_disponible"]]
        .nlargest(15, "abstencion_proyectada")
        .sort_values("abstencion_proyectada")
    )
    etiquetas = (
        top["MPIONOM"].fillna("").astype(str)
        if alcance == "municipio"
        else top["MPIONOM"].fillna("").astype(str)
        + " · sección "
        + top["SECCION"].fillna("").astype(str)
    )
    figura, eje = plt.subplots(figsize=(10, 7))
    eje.barh(etiquetas, top["abstencion_proyectada"], color="#e76f51")
    eje.xaxis.set_major_formatter(PercentFormatter(1))
    eje.set_xlabel("Abstención proyectada (%)")
    eje.set_ylabel("Zona")
    eje.set_title(f"15 zonas con mayor abstención proyectada · {alcance}")
    eje.text(
        0,
        -0.16,
        "Fuente: CCPC 2009–2024 · continuidad de la pendiente histórica",
        transform=eje.transAxes,
        fontsize=8,
        color="#586069",
    )
    guardar(figura, salida / f"topAbstencionProyectada_{alcance}")


def interpretarArgumentos() -> argparse.Namespace:
    """Define las rutas de entrada y salida."""

    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=raiz / "outputs" / "escenarios")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=raiz / "outputs" / "escenarios" / "visualizaciones",
    )
    return parser.parse_args()


def main() -> int:
    """Genera todas las visualizaciones del escenario."""

    argumentos = interpretarArgumentos()
    configurarEstilo()
    for alcance in ("seccion", "municipio"):
        datos = pd.read_csv(
            argumentos.input_root / f"ccpc_{alcance}EscenarioSinIntervencion.csv"
        )
        graficaDistribucion(datos, alcance, argumentos.output_root)
        graficaComparacion(datos, alcance, argumentos.output_root)
        graficaTop(datos, alcance, argumentos.output_root)
    print(f"Visualizaciones generadas en {argumentos.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
