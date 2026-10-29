"""Crea paquetes territoriales completos con datos y visualizaciones por entidad."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter


COLORES = {
    "azul": "#24557A",
    "azulClaro": "#76A5C3",
    "verde": "#2A9D8F",
    "amarillo": "#E9C46A",
    "rojo": "#D95D4C",
    "gris": "#8996A3",
    "tinta": "#17324D",
}
COLORES_RIESGO = {
    "bajo": COLORES["verde"],
    "medio": COLORES["amarillo"],
    "alto": COLORES["rojo"],
    "sin_historico": COLORES["gris"],
}


def obtenerRaizProyecto() -> Path:
    """Devuelve la raíz del proyecto."""

    return Path(__file__).resolve().parents[2]


def nombreSeguro(valor: str) -> str:
    """Convierte el nombre de una entidad en una carpeta portable."""

    return re.sub(r"[^a-z0-9]+", "_", str(valor).lower()).strip("_")


def configurarMatplotlib() -> None:
    """Aplica una identidad visual consistente para todos los paquetes."""

    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 240,
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelcolor": COLORES["tinta"],
            "axes.edgecolor": "#D7DEE5",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#DCE3E9",
            "grid.linewidth": 0.7,
        }
    )


def guardarGrafica(figura: plt.Figure, carpeta: Path, nombre: str) -> list[str]:
    """Guarda cada visualización en PNG y PDF."""

    carpeta.mkdir(parents=True, exist_ok=True)
    figura.tight_layout(rect=(0, 0.04, 1, 0.96))
    rutas = []
    for extension in ("png", "pdf"):
        ruta = carpeta / f"{nombre}.{extension}"
        figura.savefig(ruta, bbox_inches="tight", facecolor="white")
        rutas.append(ruta.name)
    plt.close(figura)
    return rutas


def agregarPie(figura: plt.Figure, texto: str) -> None:
    """Agrega una fuente y el alcance temporal a la figura."""

    figura.text(0.01, 0.01, texto, fontsize=8, color="#586069")


def prepararDatos(datos: pd.DataFrame) -> pd.DataFrame:
    """Normaliza tipos y agrega indicadores útiles para las gráficas."""

    datos = datos.copy()
    datos["proyeccion_disponible"] = datos["proyeccion_disponible"].astype(bool)
    datos["nivel_escenario"] = datos["nivel_escenario"].fillna("sin_historico")
    datos["cambio_abstencion_vs_base"] = pd.to_numeric(
        datos["cambio_abstencion_vs_base"], errors="coerce"
    )
    datos["abstencion_proyectada"] = pd.to_numeric(
        datos["abstencion_proyectada"], errors="coerce"
    )
    return datos


def etiquetasZonas(datos: pd.DataFrame, alcance: str) -> pd.Series:
    """Construye etiquetas legibles para rankings territoriales."""

    etiquetas = datos["MPIONOM"].fillna("Municipio sin nombre").astype(str)
    if alcance == "secciones":
        etiquetas = etiquetas + " · sección " + datos["SECCION"].astype(str)
    return etiquetas


def tieneDatosSuficientes(
    datos: pd.DataFrame, columnas: list[str], minimo: int = 2
) -> bool:
    """Indica si una visualización tiene observaciones numéricas interpretables."""

    if len(datos) < minimo:
        return False
    validos = datos[columnas].replace([np.inf, -np.inf], np.nan).dropna()
    return len(validos) >= minimo


def graficaResumen(datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path) -> list[str]:
    """Genera una ficha visual con los indicadores principales de la entidad."""

    confiables = datos[datos["proyeccion_disponible"]]
    if not tieneDatosSuficientes(
        confiables, ["latest_abstention", "abstencion_proyectada"]
    ):
        return []
    figura, ejes = plt.subplots(2, 2, figsize=(12, 8))
    figura.suptitle(f"{entidad} · Resumen territorial · {alcance.title()}", x=0.03, ha="left")

    niveles = ["bajo", "medio", "alto", "sin_historico"]
    conteo = datos["nivel_escenario"].value_counts().reindex(niveles, fill_value=0)
    ejes[0, 0].bar(
        ["Bajo", "Medio", "Alto", "Sin histórico"],
        conteo.values,
        color=[COLORES_RIESGO[nivel] for nivel in niveles],
    )
    ejes[0, 0].set_title("Zonas por nivel proyectado", loc="left")
    ejes[0, 0].set_ylabel("Número de zonas")
    ejes[0, 0].tick_params(axis="x", rotation=18)
    ejes[0, 0].bar_label(ejes[0, 0].containers[0], fmt="{:,.0f}", padding=3)

    medias = [
        datos["latest_abstention"].mean(),
        confiables["abstencion_proyectada"].mean()
        if not confiables.empty
        else np.nan,
    ]
    ejes[0, 1].bar(
        ["Observada 2024", "Proyectada 2030"],
        medias,
        color=[COLORES["azulClaro"], COLORES["rojo"]],
        width=0.58,
    )
    ejes[0, 1].yaxis.set_major_formatter(PercentFormatter(1))
    ejes[0, 1].set_ylim(0, max(medias) * 1.25 if np.isfinite(medias).any() else 1)
    ejes[0, 1].set_title("Abstención promedio", loc="left")
    ejes[0, 1].set_ylabel("Proporción")
    for contenedor in ejes[0, 1].containers:
        ejes[0, 1].bar_label(contenedor, fmt=lambda valor: f"{valor:.1%}")

    cambios = confiables["cambio_abstencion_vs_base"].dropna()
    if not cambios.empty:
        ejes[1, 0].hist(cambios, bins=12, color=COLORES["azul"], alpha=0.9)
        ejes[1, 0].axvline(0, color=COLORES["rojo"], linewidth=1.5)
        ejes[1, 0].xaxis.set_major_formatter(PercentFormatter(1))
    ejes[1, 0].set_title("Cambio esperado frente a 2024", loc="left")
    ejes[1, 0].set_xlabel("Cambio en abstención")
    ejes[1, 0].set_ylabel("Número de zonas")

    cobertura = [len(confiables), len(datos) - len(confiables)]
    ejes[1, 1].pie(
        cobertura,
        labels=["Con proyección", "Sin histórico"],
        colors=[COLORES["azul"], COLORES["gris"]],
        startangle=90,
        wedgeprops={"width": 0.42, "edgecolor": "white"},
        autopct=lambda porcentaje: f"{porcentaje:.0f}%",
    )
    ejes[1, 1].set_title("Cobertura de la simulación", loc="left")
    agregarPie(figura, "Fuente: CCPC 2009–2024 · escenario sin intervención · horizonte 2030")
    return guardarGrafica(figura, carpeta, "01_resumenTerritorial")


def graficaTop(datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path) -> list[str]:
    """Muestra las zonas con mayor abstención esperada."""

    top = datos[datos["proyeccion_disponible"]].dropna(
        subset=["abstencion_proyectada"]
    )
    if len(top) < 2:
        return []
    top = top.nlargest(15, "abstencion_proyectada")
    top = top.sort_values("abstencion_proyectada")
    if top.empty:
        return []
    figura, eje = plt.subplots(figsize=(11, 7))
    eje.barh(
        etiquetasZonas(top, alcance),
        top["abstencion_proyectada"],
        color=COLORES["rojo"],
    )
    eje.xaxis.set_major_formatter(PercentFormatter(1))
    eje.set_title(f"{entidad} · 15 zonas con mayor abstención proyectada", loc="left")
    eje.set_xlabel("Abstención proyectada en 2030")
    eje.set_ylabel("Zona")
    agregarPie(figura, "Fuente: CCPC 2009–2024 · continuidad de la tendencia histórica")
    return guardarGrafica(figura, carpeta, "02_topAbstencionProyectada")


def graficaDeterioro(datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path) -> list[str]:
    """Muestra las zonas donde más aumentaría la abstención."""

    top = datos[datos["proyeccion_disponible"]].dropna(
        subset=["cambio_abstencion_vs_base"]
    )
    if len(top) < 2:
        return []
    top = top.nlargest(15, "cambio_abstencion_vs_base")
    top = top.sort_values("cambio_abstencion_vs_base")
    if top.empty:
        return []
    figura, eje = plt.subplots(figsize=(11, 7))
    colores = [
        COLORES["rojo"] if valor > 0 else COLORES["verde"]
        for valor in top["cambio_abstencion_vs_base"]
    ]
    eje.barh(etiquetasZonas(top, alcance), top["cambio_abstencion_vs_base"], color=colores)
    eje.xaxis.set_major_formatter(PercentFormatter(1))
    eje.set_title(f"{entidad} · Mayor cambio esperado de abstención", loc="left")
    eje.set_xlabel("Cambio frente a la abstención observada en 2024")
    eje.set_ylabel("Zona")
    agregarPie(figura, "Valores positivos indican un aumento esperado bajo el escenario inercial")
    return guardarGrafica(figura, carpeta, "03_mayorDeterioroEsperado")


def graficaTendencia(datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path) -> list[str]:
    """Relaciona la pendiente histórica con la abstención proyectada."""

    confiables = datos[datos["proyeccion_disponible"]].copy()
    if not tieneDatosSuficientes(
        confiables, ["participation_slope", "abstencion_proyectada", "risk_score"]
    ):
        return []
    figura, eje = plt.subplots(figsize=(9, 6))
    eje.scatter(
        confiables["participation_slope"],
        confiables["abstencion_proyectada"],
        c=confiables["risk_score"],
        cmap="RdYlGn_r",
        vmin=0,
        vmax=100,
        alpha=0.62,
        s=28,
        edgecolors="white",
        linewidths=0.3,
    )
    eje.axvline(0, color="#667085", linewidth=1, linestyle="--")
    eje.xaxis.set_major_formatter(PercentFormatter(1))
    eje.yaxis.set_major_formatter(PercentFormatter(1))
    eje.set_title(f"{entidad} · Tendencia histórica y abstención proyectada", loc="left")
    eje.set_xlabel("Pendiente histórica de participación")
    eje.set_ylabel("Abstención proyectada en 2030")
    agregarPie(figura, "Color: índice de riesgo histórico (0–100) · cada punto representa una zona")
    return guardarGrafica(figura, carpeta, "04_tendenciaVsAbstencion")


def graficaComparacionRiesgo(datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path) -> list[str]:
    """Compara el nivel histórico con el nivel del escenario."""

    comparables = datos.dropna(subset=["risk_level", "nivel_escenario"])
    if len(comparables) < 2 or comparables["risk_level"].nunique() < 2:
        return []
    tabla = pd.crosstab(
        comparables["risk_level"].fillna("sin_historico"),
        comparables["nivel_escenario"],
    ).reindex(
        index=["bajo", "medio", "alto", "sin_historico"],
        columns=["bajo", "medio", "alto", "sin_historico"],
        fill_value=0,
    )
    figura, eje = plt.subplots(figsize=(8, 6))
    imagen = eje.imshow(tabla.values, cmap="Blues")
    figura.colorbar(imagen, ax=eje, label="Número de zonas")
    eje.set_xticks(range(4), ["Bajo", "Medio", "Alto", "Sin histórico"])
    eje.set_yticks(range(4), ["Bajo", "Medio", "Alto", "Sin histórico"])
    eje.set_xlabel("Nivel en escenario 2030")
    eje.set_ylabel("Nivel de riesgo histórico")
    eje.set_title(f"{entidad} · Matriz de transición de niveles", loc="left")
    for fila in range(4):
        for columna in range(4):
            eje.text(columna, fila, f"{tabla.iloc[fila, columna]:,}", ha="center", va="center")
    agregarPie(figura, "La matriz permite identificar permanencias y cambios de prioridad territorial")
    return guardarGrafica(figura, carpeta, "05_matrizTransicionRiesgo")


def graficaPerfilHistorico(
    datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path
) -> list[str]:
    """Resume participación, abstención y pendiente del histórico disponible."""

    participacion = datos["latest_participation"].dropna()
    continuidad = datos["years_observed"].dropna()
    if len(participacion) < 2 or len(continuidad) < 2:
        return []
    figura, ejes = plt.subplots(1, 2, figsize=(11, 4.8))
    figura.suptitle(f"{entidad} · Perfil histórico disponible · {alcance.title()}", x=0.03, ha="left")
    ejes[0].hist(
        participacion,
        bins=12,
        color=COLORES["azulClaro"],
        alpha=0.9,
    )
    ejes[0].xaxis.set_major_formatter(PercentFormatter(1))
    ejes[0].set_title("Participación observada más reciente", loc="left")
    ejes[0].set_xlabel("Participación")
    ejes[0].set_ylabel("Número de zonas")
    ejes[1].hist(
        continuidad,
        bins=range(1, int(datos["years_observed"].max()) + 2)
        if datos["years_observed"].notna().any()
        else 1,
        color=COLORES["azul"],
        alpha=0.9,
        align="left",
        rwidth=0.85,
    )
    ejes[1].set_title("Continuidad histórica por zona", loc="left")
    ejes[1].set_xlabel("Número de elecciones observadas")
    ejes[1].set_ylabel("Número de zonas")
    agregarPie(figura, "Fuente: CCPC 2009–2024 · perfil descriptivo, no causal")
    return guardarGrafica(figura, carpeta, "06_perfilHistorico")


def graficaCalidadCobertura(
    datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path
) -> list[str]:
    """Expone la cobertura y disponibilidad de la simulación."""

    if len(datos) < 2:
        return []
    indicadores = {
        "Con histórico suficiente": int(datos["proyeccion_disponible"].sum()),
        "Sin histórico suficiente": int((~datos["proyeccion_disponible"]).sum()),
        "Con tendencia descendente": int(datos["declining_participation"].gt(0).sum()),
    }
    figura, eje = plt.subplots(figsize=(9, 4.8))
    barras = eje.barh(
        list(indicadores.keys()),
        list(indicadores.values()),
        color=[COLORES["azul"], COLORES["gris"], COLORES["rojo"]],
    )
    eje.set_title(f"{entidad} · Cobertura y señales de atención · {alcance.title()}", loc="left")
    eje.set_xlabel("Número de zonas")
    eje.bar_label(barras, fmt="{:,.0f}", padding=4)
    agregarPie(figura, "Una zona sin histórico no se interpreta como bajo riesgo")
    return guardarGrafica(figura, carpeta, "07_coberturaYCalidad")


def generarVisualizaciones(
    datos: pd.DataFrame, entidad: str, alcance: str, carpeta: Path
) -> list[str]:
    """Genera el conjunto completo de visualizaciones de un alcance."""

    datos = prepararDatos(datos)
    nombres = []
    nombres += graficaResumen(datos, entidad, alcance, carpeta)
    nombres += graficaTop(datos, entidad, alcance, carpeta)
    nombres += graficaDeterioro(datos, entidad, alcance, carpeta)
    nombres += graficaTendencia(datos, entidad, alcance, carpeta)
    nombres += graficaComparacionRiesgo(datos, entidad, alcance, carpeta)
    nombres += graficaPerfilHistorico(datos, entidad, alcance, carpeta)
    nombres += graficaCalidadCobertura(datos, entidad, alcance, carpeta)
    return nombres


def crearPaqueteEntidad(
    entidad: str,
    secciones: pd.DataFrame,
    municipios: pd.DataFrame,
    carpeta: Path,
) -> dict[str, object]:
    """Escribe datos, resumen y visualizaciones de una entidad."""

    carpeta.mkdir(parents=True, exist_ok=True)
    secciones = secciones[secciones["EDONOM"].eq(entidad)].copy()
    municipios = municipios[municipios["EDONOM"].eq(entidad)].copy()
    secciones.to_csv(carpeta / "datos_secciones_escenario.csv", index=False)
    municipios.to_csv(carpeta / "datos_municipios_escenario.csv", index=False)

    visualizaciones = {}
    visualizaciones["secciones"] = generarVisualizaciones(
        secciones, entidad, "secciones", carpeta / "visualizaciones" / "secciones"
    )
    visualizaciones["municipios"] = generarVisualizaciones(
        municipios, entidad, "municipios", carpeta / "visualizaciones" / "municipios"
    )
    resumen = {
        "entidad": entidad,
        "horizonte": 2030,
        "secciones": int(len(secciones)),
        "municipios": int(len(municipios)),
        "secciones_con_proyeccion": int(secciones["proyeccion_disponible"].sum()),
        "municipios_con_proyeccion": int(municipios["proyeccion_disponible"].sum()),
        "abstencion_secciones_2030": float(secciones["abstencion_proyectada"].mean()),
        "abstencion_municipios_2030": float(municipios["abstencion_proyectada"].mean()),
        "visualizaciones": visualizaciones,
    }
    (carpeta / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resumen


def interpretarArgumentos() -> argparse.Namespace:
    """Define las rutas del empaquetado territorial."""

    raiz = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=raiz / "outputs" / "escenarios")
    parser.add_argument("--output-root", type=Path, default=raiz / "outputs" / "entidades")
    return parser.parse_args()


def main() -> int:
    """Construye los 32 paquetes estatales y el resumen nacional."""

    argumentos = interpretarArgumentos()
    configurarMatplotlib()
    secciones = pd.read_csv(
        argumentos.input_root / "ccpc_seccionEscenarioSinIntervencion.csv",
        low_memory=False,
    )
    municipios = pd.read_csv(
        argumentos.input_root / "ccpc_municipioEscenarioSinIntervencion.csv",
        low_memory=False,
    )
    entidades = sorted(
        set(secciones["EDONOM"].dropna()) | set(municipios["EDONOM"].dropna())
    )
    reportes = []
    for entidad in entidades:
        reportes.append(
            crearPaqueteEntidad(
                str(entidad),
                secciones,
                municipios,
                argumentos.output_root / nombreSeguro(str(entidad)),
            )
        )

    resumenNacional = crearPaqueteEntidad(
        "Resumen nacional",
        secciones.assign(EDONOM="Resumen nacional"),
        municipios.assign(EDONOM="Resumen nacional"),
        argumentos.output_root / "resumen_nacional",
    )
    manifiesto = {
        "descripcion": "Paquetes territoriales del escenario sin intervención",
        "horizonte": 2030,
        "entidades_federativas": len(entidades),
        "paquetes": reportes,
        "resumen_nacional": resumenNacional,
    }
    (argumentos.output_root / "manifest.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    archivoZip = shutil.make_archive(
        str(argumentos.output_root.parent / "paquete_territorial_escenario_2030"),
        "zip",
        root_dir=argumentos.output_root,
    )
    print(f"Paquetes generados: {len(entidades)} entidades + resumen nacional")
    print(f"Archivo distribuible: {archivoZip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
