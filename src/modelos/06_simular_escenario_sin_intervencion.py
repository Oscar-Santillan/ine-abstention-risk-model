"""Simular escenario sin intervención - Proyección 2030.

Proyecta la abstención electoral hacia 2030 suponiendo que continúa la
pendiente histórica de participación, para municipios y secciones.

Fórmulas:
- participacion_proyectada = clip(latest_participation + slope * (ano_proyectado - ano_base), 0, 1)
- abstencion_proyectada    = clip((latest_participation + latest_abstention) - participacion_proyectada, 0, 1)
- cambio_abstencion_vs_base = abstencion_proyectada - latest_abstention
- nivel_escenario: percentiles 33.3 / 66.7 -> bajo / medio / alto
- confiabilidad_proyeccion: aalta si hay tendencia confiable y >= 3 años, baja en otro caso
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

METODO = "continuidad de pendiente histórica"
MIN_ANOS = 3


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _num(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


def calcular_escenario(df: pd.DataFrame, ano_base: int, ano_proyectado: int) -> pd.DataFrame:
    df = df.copy()

    slope = _num(df, "participation_slope")
    latest_part = _num(df, "latest_participation")
    latest_abs = _num(df, "latest_abstention")
    years = _num(df, "years_observed")

    if "trend_reliable" in df.columns:
        reliable = df["trend_reliable"].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        reliable = pd.Series(False, index=df.index)

    tiene_dato_base = (latest_part + latest_abs) > 0.01
    disponible = tiene_dato_base

    # Calcular proyeccion: usar slope si está disponible, sino usar latest como proyección inercial
    slope_filled = slope.fillna(0)
    horizonte = ano_proyectado - ano_base
    part_proj = (latest_part + slope_filled * horizonte).clip(0, 1)
    # Para zonas sin tendencia confiable, usar participación actual como proyección
    part_proj = np.where(reliable & (years >= MIN_ANOS), part_proj, latest_part)
    abs_proj = ((latest_part + latest_abs) - part_proj).clip(0, 1)

    # Nivel de confiabilidad de la proyección
    confiabilidad = np.select(
        [reliable & (years >= MIN_ANOS) & disponible],
        ["alta"],
        default="baja",
    )
    df["confiabilidad_proyeccion"] = confiabilidad

    df["ano_base"] = ano_base
    df["ano_proyectado"] = ano_proyectado
    df["metodo_escenario"] = METODO
    df["proyeccion_disponible"] = disponible
    df["participacion_proyectada"] = pd.Series(part_proj, index=df.index).where(disponible)
    df["abstencion_proyectada"] = pd.Series(abs_proj, index=df.index).where(disponible)
    df["cambio_abstencion_vs_base"] = (pd.Series(abs_proj, index=df.index) - latest_abs).where(disponible)

    pct = df["abstencion_proyectada"].rank(pct=True) * 100
    df["percentil_abstencion_proyectada"] = pct

    df["nivel_escenario"] = np.select(
        [~disponible, pct >= 66.7, pct >= 33.3],
        ["sin_historico", "alto", "medio"],
        default="bajo",
    )
    df["razon_escenario"] = np.select(
        [~disponible, df["cambio_abstencion_vs_base"] > 0],
        [
            "sin histórico suficiente o sin datos base registrados",
            "la tendencia histórica aumenta la abstención esperada",
        ],
        default="la tendencia histórica no aumenta la abstención esperada",
    )
    # Añadir condicion para zonas con confiabilidad baja
    idx_baja_conf = (disponible) & (confiabilidad == "baja")
    df.loc[idx_baja_conf, "razon_escenario"] = "proyeccion estimada con datos limitados"
    return df


def simular_escenario(risk_csv: Path, output_csv: Path, ano_base: int = 2024, ano_proyectado: int = 2030) -> pd.DataFrame:
    df = pd.read_csv(risk_csv, encoding="utf-8", on_bad_lines="warn")
    print(f"  Datos cargados: {len(df)} filas")
    df = calcular_escenario(df, ano_base, ano_proyectado)
    tmp = output_csv.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(output_csv)
    print(f"  Escenario guardado: {output_csv} ({len(df)} filas)")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Simular escenario sin intervención 2030")
    parser.add_argument("--risk-dir", type=Path, default=_project_root() / "outputs" / "risk")
    parser.add_argument("--output-dir", type=Path, default=_project_root() / "outputs" / "escenarios")
    parser.add_argument("--ano-base", type=int, default=2024)
    parser.add_argument("--ano-proyectado", type=int, default=2030)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    trabajos = [
        ("municipios", "ccpc_municipality_risk_index.csv", "ccpc_municipioEscenarioSinIntervencion.csv"),
        ("secciones", "ccpc_section_risk_index.csv", "ccpc_seccionEscenarioSinIntervencion.csv"),
    ]
    for nombre, entrada, salida in trabajos:
        src = args.risk_dir / entrada
        if src.exists():
            print(f"Procesando {nombre}...")
            simular_escenario(src, args.output_dir / salida, args.ano_base, args.ano_proyectado)
        else:
            print(f"ADVERTENCIA: no se encontró {src}")


if __name__ == "__main__":
    main()
