"""Simula la continuidad de las tendencias electorales sin intervención."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ANO_BASE = 2024
INTERVALO_ELECTORAL = 6
ANO_PROYECTADO = ANO_BASE + INTERVALO_ELECTORAL
NIVELES_RIESGO = ["bajo", "medio", "alto"]


def obtenerRaizProyecto() -> Path:
    """Devuelve la carpeta raíz del proyecto."""

    return Path(__file__).resolve().parents[2]


def obtenerClavesTerritoriales(datos: pd.DataFrame, alcance: str) -> list[str]:
    """Selecciona las columnas que identifican un municipio o una sección."""

    claves = ["EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM"]
    if alcance == "seccion":
        claves += ["SECCION", "TIPOSEC"]
    return claves


def calcularPercentil(datos: pd.Series) -> pd.Series:
    """Convierte una variable numérica en una escala comparable de 0 a 100."""

    cantidad = datos.notna().sum()
    if cantidad <= 1:
        return datos.where(datos.notna(), np.nan)
    return datos.rank(method="average").sub(1).div(cantidad - 1).mul(100)


def proyectarAlcance(datos: pd.DataFrame, alcance: str) -> tuple[pd.DataFrame, dict[str, object]]:
    """Calcula el escenario inercial para un nivel territorial."""

    claves = obtenerClavesTerritoriales(datos, alcance)
    columnas = claves + [
        "years_observed",
        "participation_slope",
        "latest_participation",
        "latest_abstention",
        "latest_non_specified",
        "declining_participation",
        "trend_reliable",
        "risk_score",
        "risk_level",
        "risk_reason",
    ]
    faltantes = [columna for columna in columnas if columna not in datos.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas para {alcance}: {', '.join(faltantes)}")

    resultado = datos[columnas].copy()
    confiable = resultado["trend_reliable"] & resultado["participation_slope"].notna()
    participacion_disponible = (
        resultado["latest_participation"] + resultado["latest_abstention"]
    )
    cambio_participacion = resultado["participation_slope"] * INTERVALO_ELECTORAL
    participacion_proyectada = (
        resultado["latest_participation"] + cambio_participacion
    ).clip(lower=0)
    participacion_proyectada = pd.concat(
        [participacion_proyectada, participacion_disponible], axis=1
    ).min(axis=1)
    abstencion_proyectada = participacion_disponible - participacion_proyectada
    abstencion_proyectada = abstencion_proyectada.clip(lower=0)

    resultado["ano_base"] = ANO_BASE
    resultado["ano_proyectado"] = ANO_PROYECTADO
    resultado["metodo_escenario"] = "continuidad de pendiente histórica"
    resultado["participacion_proyectada"] = participacion_proyectada.where(confiable)
    resultado["abstencion_proyectada"] = abstencion_proyectada.where(confiable)
    resultado["cambio_abstencion_vs_base"] = (
        resultado["abstencion_proyectada"] - resultado["latest_abstention"]
    ).where(confiable)
    resultado["proyeccion_disponible"] = confiable

    resultado["percentil_abstencion_proyectada"] = calcularPercentil(
        resultado["abstencion_proyectada"].where(confiable)
    )
    resultado["nivel_escenario"] = pd.cut(
        resultado["percentil_abstencion_proyectada"],
        bins=[-np.inf, 33.333333, 66.666667, np.inf],
        labels=NIVELES_RIESGO,
    ).astype("string")
    resultado.loc[~confiable, "nivel_escenario"] = "sin_historico"
    resultado["razon_escenario"] = np.where(
        confiable & (resultado["cambio_abstencion_vs_base"] > 0),
        "la tendencia histórica aumenta la abstención esperada",
        np.where(
            confiable,
            "la tendencia histórica no aumenta la abstención esperada",
            "proyección no disponible por histórico insuficiente",
        ),
    )

    resultado = resultado.sort_values(
        ["abstencion_proyectada"] + claves,
        ascending=[False] + [True] * len(claves),
        na_position="last",
    )
    return resultado, {
        "alcance": alcance,
        "zonas": int(len(resultado)),
        "zonas_con_proyeccion": int(confiable.sum()),
        "zonas_sin_historico": int((~confiable).sum()),
        "abstencion_proyectada_promedio": float(
            resultado["abstencion_proyectada"].mean()
        ),
        "aumento_promedio_vs_base": float(
            resultado["cambio_abstencion_vs_base"].mean()
        ),
        "niveles_escenario": resultado["nivel_escenario"]
        .value_counts(dropna=False)
        .to_dict(),
    }


def interpretarArgumentos() -> argparse.Namespace:
    """Define las rutas de entrada y salida del escenario."""

    raiz = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root",
        type=Path,
        default=raiz / "outputs" / "resultadosIntegrados",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=raiz / "outputs" / "escenarios",
    )
    return parser.parse_args()


def main() -> int:
    """Ejecuta y documenta el escenario sin intervención."""

    argumentos = interpretarArgumentos()
    manifiesto = {
        "project_area": "escenario_sin_intervencion",
        "descripcion": (
            "Proyección inercial que extiende seis años la pendiente histórica "
            "de participación observada hasta 2024."
        ),
        "ano_base": ANO_BASE,
        "ano_proyectado": ANO_PROYECTADO,
        "intervalo_electoral": INTERVALO_ELECTORAL,
        "supuestos": [
            "No se implementan acciones adicionales de movilización.",
            "La pendiente histórica continúa desde 2024 hasta 2030.",
            "La proyección se limita al intervalo disponible de participación y abstención.",
            "Las zonas con menos de tres años observados no reciben una proyección.",
            "El resultado es un escenario hipotético, no una estimación causal.",
        ],
        "alcances": [],
    }
    for alcance, nombre in (
        ("seccion", "ccpc_seccionResultadosIntegrados.csv"),
        ("municipio", "ccpc_municipioResultadosIntegrados.csv"),
    ):
        datos = pd.read_csv(argumentos.input_root / nombre, low_memory=False)
        resultado, resumen = proyectarAlcance(datos, alcance)
        argumentos.output_root.mkdir(parents=True, exist_ok=True)
        salida = argumentos.output_root / f"ccpc_{alcance}EscenarioSinIntervencion.csv"
        resultado.to_csv(salida, index=False)
        resumen["entrada"] = str(argumentos.input_root / nombre)
        resumen["salida"] = str(salida)
        manifiesto["alcances"].append(resumen)

    argumentos.output_root.mkdir(parents=True, exist_ok=True)
    (argumentos.output_root / "manifiestoEscenarioSinIntervencion.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for alcance in manifiesto["alcances"]:
        print(
            f"{alcance['alcance']}: "
            f"{alcance['zonas_con_proyeccion']:,} zonas proyectadas"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
