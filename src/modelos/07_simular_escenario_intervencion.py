"""Simulación 2 - Escenario CON intervención (proyección 2030).

Toma el escenario sin intervención (Simulación 1) y aplica tres propuestas
sobre la abstención proyectada:
  P1  Árbol de Influencers + Red de Embajadores Electorales
  P2  Campaña de Rescate Cívico con Monitoreo de Movilidad
  P3  Plataforma Cívica Digital Gamificada

Perfiles (se derivan de columnas que sí existen en los CSV de escenario):
  A  abstención base crítica      -> risk_level == "alto"
  B  deterioro acelerado          -> risk_reason contiene "descendente"
  C  inestabilidad cíclica        -> risk_reason contiene "inestable"
  Prioridad A > B > C (perfiles excluyentes). Las zonas sin proyección
  ("sin_historico") no reciben intervención simulada.

Los efectos (pp de reducción) son SUPUESTOS de diseño de cada propuesta, no
estimaciones causales; por eso se reportan tres escenarios de sensibilidad.

Salidas:
  outputs/escenarios/ccpc_municipioEscenarioConIntervencion.csv
  outputs/escenarios/ccpc_seccionEscenarioConIntervencion.csv
  outputs/escenarios/ccpc_sensibilidadIntervencion.csv
  docs/informe_simulacion_2.md
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ESCENARIOS_SENSIBILIDAD = {"conservador": 0.5, "base": 1.0, "optimista": 1.5}
PERFILES = ["A", "B", "C", "sin_perfil"]
DESCRIPCION_PERFIL = {
    "A": "Abstención base crítica (riesgo alto)",
    "B": "Deterioro acelerado (tendencia descendente)",
    "C": "Inestabilidad cíclica (participación inestable)",
    "sin_perfil": "Con proyección pero sin señal de riesgo específica",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- perfiles
def asignar_perfil(df: pd.DataFrame) -> pd.Series:
    """Perfil excluyente por zona (A > B > C); 'sin_proyeccion' si no hay proyección."""
    razon = df["risk_reason"].fillna("").astype(str).str.lower()
    nivel = df["risk_level"].fillna("").astype(str).str.lower()
    disp = df["proyeccion_disponible"].fillna(False).astype(bool)

    perfil = pd.Series("sin_perfil", index=df.index)
    perfil[razon.str.contains("inestable", regex=False)] = "C"
    perfil[razon.str.contains("descendente", regex=False)] = "B"
    perfil[nivel == "alto"] = "A"
    perfil[~disp] = "sin_proyeccion"
    return perfil


def efectos_por_perfil(cobertura_movilidad: float) -> dict:
    """Reducción esperada de abstención (proporción 0-1) por propuesta y perfil."""
    return {
        "A": {"P1": 0.030},
        "B": {"P1": 0.010, "P2": 0.040 * cobertura_movilidad},
        "C": {"P1": 0.005, "P3": 0.050},
    }


# --------------------------------------------------------------- simulación
def calcular_cortes(df: pd.DataFrame) -> tuple[float, float]:
    """Cortes de nivel (percentil 33.3 y 66.7) del escenario BASE."""
    base = df.loc[df["proyeccion_disponible"].fillna(False).astype(bool), "abstencion_proyectada"].dropna()
    return float(base.quantile(1 / 3)), float(base.quantile(2 / 3))


def clasificar(serie: pd.Series, cortes: tuple[float, float]) -> pd.Series:
    """Nivel alto/medio/bajo con cortes FIJOS (los del escenario base)."""
    return pd.Series(
        np.select(
            [serie.isna(), serie >= cortes[1], serie >= cortes[0]],
            ["sin_historico", "alto", "medio"],
            default="bajo",
        ),
        index=serie.index,
    )


def aplicar_intervencion(df: pd.DataFrame, factor: float, cobertura: float, tope_pp: float,
                         cortes: tuple[float, float]) -> pd.DataFrame:
    """Agrega columnas del escenario con intervención."""
    out = df.copy()
    out["perfil_intervencion"] = asignar_perfil(out)
    disp = out["proyeccion_disponible"].fillna(False).astype(bool)

    reduccion = pd.Series(0.0, index=out.index)
    propuestas = pd.Series("ninguna", index=out.index)
    for perfil, efectos in efectos_por_perfil(cobertura).items():
        mask = (out["perfil_intervencion"] == perfil) & disp
        reduccion.loc[mask] = sum(efectos.values())
        propuestas.loc[mask] = "+".join(efectos.keys())

    reduccion = (reduccion * factor).clip(upper=tope_pp / 100)
    base = out["abstencion_proyectada"]
    nuevo = (base - reduccion).clip(0, 1)
    real = (base - nuevo).where(disp)

    out["propuestas_aplicadas"] = propuestas
    out["reduccion_abstencion_pp"] = real * 100
    out["abstencion_proyectada_intervencion"] = nuevo.where(disp)
    out["participacion_proyectada_intervencion"] = (out["participacion_proyectada"] + real).clip(0, 1).where(disp)
    out["cambio_abstencion_vs_base_intervencion"] = (
        out["abstencion_proyectada_intervencion"] - out["latest_abstention"]
    )
    out["nivel_base_ref"] = clasificar(base.where(disp), cortes)
    out["nivel_escenario_intervencion"] = clasificar(out["abstencion_proyectada_intervencion"], cortes)
    return out


# ----------------------------------------------------------------- métricas
def resumir(df: pd.DataFrame) -> dict:
    disp = df["proyeccion_disponible"].fillna(False).astype(bool)
    av = df[disp]
    res = {
        "zonas": len(df),
        "con_proyeccion": int(disp.sum()),
        "sin_proyeccion": int((~disp).sum()),
        "abs_base_pct": float(av["abstencion_proyectada"].mean() * 100),
        "abs_int_pct": float(av["abstencion_proyectada_intervencion"].mean() * 100),
        "reduccion_pp": float(av["reduccion_abstencion_pp"].mean()),
        "alto_base": int((av["nivel_base_ref"] == "alto").sum()),
        "alto_int": int((av["nivel_escenario_intervencion"] == "alto").sum()),
        "salen_de_alto": int(((av["nivel_base_ref"] == "alto") & (av["nivel_escenario_intervencion"] != "alto")).sum()),
        "intervenidas": int((av["propuestas_aplicadas"] != "ninguna").sum()),
        "votos_evitados": None,
    }
    if "latest_ln" in df.columns:
        res["votos_evitados"] = float((av["reduccion_abstencion_pp"] / 100 * av["latest_ln"]).sum())

    por_perfil = {}
    for p in PERFILES:
        sub = av[av["perfil_intervencion"] == p]
        por_perfil[p] = {
            "n": len(sub),
            "abs_base_pct": float(sub["abstencion_proyectada"].mean() * 100) if len(sub) else float("nan"),
            "abs_int_pct": float(sub["abstencion_proyectada_intervencion"].mean() * 100) if len(sub) else float("nan"),
            "reduccion_pp": float(sub["reduccion_abstencion_pp"].mean()) if len(sub) else float("nan"),
        }
    res["por_perfil"] = por_perfil
    return res


def _tabla(encabezados: list, filas: list) -> str:
    lineas = ["| " + " | ".join(encabezados) + " |", "|" + "|".join("---" for _ in encabezados) + "|"]
    lineas += ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]
    return "\n".join(lineas)


def _fmt(x, dec=2):
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{dec}f}"


def generar_informe(resumenes: dict, sens: pd.DataFrame, params: dict, ruta: Path) -> None:
    secc = []
    for alcance, r in resumenes.items():
        filas = [[p, DESCRIPCION_PERFIL[p], r["por_perfil"][p]["n"], _fmt(r["por_perfil"][p]["abs_base_pct"]),
                  _fmt(r["por_perfil"][p]["abs_int_pct"]), _fmt(r["por_perfil"][p]["reduccion_pp"])]
                 for p in PERFILES]
        votos = "n/d (los CSV no incluyen lista nominal)" if r["votos_evitados"] is None else f"{r['votos_evitados']:,.0f}"
        secc.append(
            f"### {alcance.capitalize()}\n\n"
            + _tabla(["Métrica", "Valor"], [
                ["Zonas totales", f"{r['zonas']:,}"],
                ["Zonas con proyección", f"{r['con_proyeccion']:,}"],
                ["Zonas sin proyección (sin histórico)", f"{r['sin_proyeccion']:,}"],
                ["Zonas intervenidas", f"{r['intervenidas']:,}"],
                ["Abstención media 2030, sin intervención (%)", _fmt(r["abs_base_pct"])],
                ["Abstención media 2030, con intervención (%)", _fmt(r["abs_int_pct"])],
                ["Reducción media (pp)", _fmt(r["reduccion_pp"])],
                ["Zonas en nivel alto (base → intervención)", f"{r['alto_base']:,} → {r['alto_int']:,}"],
                ["Zonas que salen del nivel alto", f"{r['salen_de_alto']:,}"],
                ["Votos adicionales estimados", votos],
            ])
            + "\n\n**Por perfil**\n\n"
            + _tabla(["Perfil", "Descripción", "Zonas", "Abs. base (%)", "Abs. interv. (%)", "Reducción (pp)"], filas)
        )

    sens_tabla = _tabla(
        list(sens.columns),
        [[(_fmt(v) if isinstance(v, float) else v) for v in fila] for fila in sens.itertuples(index=False)],
    )

    texto = f"""# Informe Simulación 2: escenario con intervención

Generado: {datetime.now():%Y-%m-%d %H:%M}  
Reto 2 INE: predicción y escenarios de riesgo de abstención.

## 1. Qué se simuló

Sobre la abstención proyectada a {params['ano']} (escenario sin intervención) se aplican tres propuestas
según el perfil de cada zona:

| Perfil | Propuestas | Reducción asumida (escenario base) |
|---|---|---|
| A | P1 Árbol de Influencers + Red de Embajadores | -3.0 pp |
| B | P1 + P2 Rescate Cívico con Monitoreo de Movilidad | -1.0 pp (P1) y -4.0 pp x cobertura {params['cobertura']:.0%} (P2) |
| C | P1 + P3 Plataforma Cívica Gamificada | -0.5 pp (P1) y -5.0 pp (P3) |

Tope de reducción por zona: {params['tope']:.1f} pp.

## 2. Resultados

{chr(10).join(secc)}

## 3. Sensibilidad (municipios)

Los efectos de cada propuesta son supuestos de diseño. Se escalan x0.5, x1.0 y x1.5 para mostrar el rango:

{sens_tabla}

## 4. Limitaciones

- Los efectos por propuesta no están estimados con datos experimentales; son hipótesis a validar con pilotos.
- Los perfiles se definen con `risk_level` y `risk_reason`. Los CSV de escenario no traen edad ni volatilidad,
  así que el perfil C es un proxy de inestabilidad, no de juventud.
- Las zonas sin histórico suficiente no tienen proyección y no se simulan; requieren otra estrategia (recolección de datos).
- La cobertura de movilidad es un parámetro, no un dato observado.
"""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


# --------------------------------------------------------------------- main
def _guardar(df: pd.DataFrame, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(ruta)


def main() -> None:
    raiz = _project_root()
    ap = argparse.ArgumentParser(description="Simulación 2: escenario con intervención")
    ap.add_argument("--escenarios-dir", type=Path, default=raiz / "outputs" / "escenarios")
    ap.add_argument("--docs-dir", type=Path, default=raiz / "docs")
    ap.add_argument("--cobertura-movilidad", type=float, default=0.6, help="Fracción 0-1 de cobertura de P2")
    ap.add_argument("--factor", type=float, default=1.0, help="Multiplicador de efectos (escenario base = 1.0)")
    ap.add_argument("--tope-pp", type=float, default=8.0, help="Reducción máxima por zona en pp")
    args = ap.parse_args()

    entradas = {
        "municipios": ("ccpc_municipioEscenarioSinIntervencion.csv", "ccpc_municipioEscenarioConIntervencion.csv"),
        "secciones": ("ccpc_seccionEscenarioSinIntervencion.csv", "ccpc_seccionEscenarioConIntervencion.csv"),
    }
    resumenes, sens_filas, ano = {}, [], 2030

    for alcance, (entrada, salida) in entradas.items():
        src = args.escenarios_dir / entrada
        if not src.exists():
            print(f"ADVERTENCIA: no se encontró {src}")
            continue
        print(f"Procesando {alcance}...")
        df = pd.read_csv(src, encoding="utf-8")
        ano = int(df["ano_proyectado"].dropna().iloc[0]) if "ano_proyectado" in df else ano
        cortes = calcular_cortes(df)

        res_df = aplicar_intervencion(df, args.factor, args.cobertura_movilidad, args.tope_pp, cortes)
        _guardar(res_df, args.escenarios_dir / salida)
        resumenes[alcance] = resumir(res_df)
        r = resumenes[alcance]
        print(f"  {r['con_proyeccion']:,} zonas con proyección | intervenidas: {r['intervenidas']:,} | "
              f"abstención {r['abs_base_pct']:.2f}% -> {r['abs_int_pct']:.2f}% ({r['reduccion_pp']:.2f} pp)")
        print("  perfiles: " + ", ".join(f"{p}={r['por_perfil'][p]['n']}" for p in PERFILES))

        if alcance == "municipios":
            for nombre, f in ESCENARIOS_SENSIBILIDAD.items():
                s = resumir(aplicar_intervencion(df, f, args.cobertura_movilidad, args.tope_pp, cortes))
                sens_filas.append({"escenario": nombre, "factor": f, "abs_media_interv_pct": s["abs_int_pct"],
                                   "reduccion_media_pp": s["reduccion_pp"], "salen_de_alto": s["salen_de_alto"]})

    if not resumenes:
        raise SystemExit("No se encontró ningún escenario base. Corre primero 06_simular_escenario_sin_intervencion.py")

    sens = pd.DataFrame(sens_filas)
    if not sens.empty:
        _guardar(sens, args.escenarios_dir / "ccpc_sensibilidadIntervencion.csv")
    generar_informe(resumenes, sens, {"ano": ano, "cobertura": args.cobertura_movilidad, "tope": args.tope_pp},
                    args.docs_dir / "informe_simulacion_2.md")
    print(f"\nInforme: {args.docs_dir / 'informe_simulacion_2.md'}")


if __name__ == "__main__":
    main()

