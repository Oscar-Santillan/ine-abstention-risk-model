"""Empaquetar entidades - Fase 4.

Por entidad federativa genera:
- datos_municipios_escenario.csv
- datos_secciones_escenario.csv
- resumen.json
(+ las visualizaciones ya generadas en la misma carpeta)

Además genera resumen_nacional.json y paquete_territorial_escenario_2030.zip
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Dict, List

import pandas as pd


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_resumen(df: pd.DataFrame, entidad: str) -> Dict:
    """Resumen JSON de una entidad."""
    total = len(df)
    if "proyeccion_disponible" in df.columns:
        disponible = df["proyeccion_disponible"].fillna(False).astype(bool)
    else:
        disponible = pd.Series(False, index=df.index)
    av = df[disponible]

    dist = {k: int((av["nivel_escenario"] == k).sum()) for k in ("alto", "medio", "bajo")}
    dist["sin_historico"] = total - len(av)

    def media(col: str):
        return round(float(av[col].mean()), 6) if len(av) and col in av.columns else None

    return {
        "entidad": entidad,
        "total_zonas": total,
        "zonas_con_proyeccion": len(av),
        "sin_historico": total - len(av),
        "abstencion_promedio_2024": media("latest_abstention"),
        "abstencion_promedio_2030": media("abstencion_proyectada"),
        "cambio_promedio": media("cambio_abstencion_vs_base"),
        "distribucion_escenario": dist,
    }


def _empaquetar_entidad(df_mun: pd.DataFrame, df_sec: pd.DataFrame, entidad: str, output_dir: Path) -> Dict:
    out_dir = _ensure_dir(output_dir / entidad.lower().replace(" ", "_"))

    if not df_mun.empty:
        df_mun.to_csv(out_dir / "datos_municipios_escenario.csv", index=False, encoding="utf-8")
    if not df_sec.empty:
        df_sec.to_csv(out_dir / "datos_secciones_escenario.csv", index=False, encoding="utf-8")

    resumen = _build_resumen(df_mun if not df_mun.empty else df_sec, entidad)
    (out_dir / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resumen


def _build_resumen_nacional(resumenes: List[Dict]) -> Dict:
    total = sum(r["total_zonas"] for r in resumenes)
    con = sum(r["zonas_con_proyeccion"] for r in resumenes)
    return {
        "total_entidades": len(resumenes),
        "total_zonas": total,
        "zonas_con_proyeccion": con,
        "sin_historico": sum(r["sin_historico"] for r in resumenes),
        "porcentaje_con_proyeccion": round(con / total * 100, 2) if total else 0,
        "entidades": [r["entidad"] for r in resumenes],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Empaquetar entidades - Escenario 2030")
    parser.add_argument("--escenarios-dir", type=Path, default=_project_root() / "outputs" / "escenarios")
    parser.add_argument("--output-dir", type=Path, default=_project_root() / "outputs" / "entidades")
    parser.add_argument("--zip-name", type=str, default="paquete_territorial_escenario_2030.zip")
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

    _ensure_dir(args.output_dir)
    resumenes = []
    for entidad in entidades:
        print(f"Empaquetando {entidad}...")
        df_m = df_mun[df_mun["EDONOM"] == entidad].copy() if not df_mun.empty else pd.DataFrame()
        df_s = df_sec[df_sec["EDONOM"] == entidad].copy() if not df_sec.empty else pd.DataFrame()
        resumenes.append(_empaquetar_entidad(df_m, df_s, entidad, args.output_dir))

    nacional_path = args.output_dir / "resumen_nacional.json"
    nacional_path.write_text(
        json.dumps(_build_resumen_nacional(resumenes), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    zip_path = args.output_dir / args.zip_name
    archivos = [p for p in args.output_dir.rglob("*") if p.is_file() and p.name != args.zip_name]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in archivos:
            zf.write(p, p.relative_to(args.output_dir))

    print(f"\nPaquete ZIP: {zip_path}")
    print(f"Total entidades: {len(entidades)}")
    print(f"Resumen nacional: {nacional_path}")


if __name__ == "__main__":
    main()