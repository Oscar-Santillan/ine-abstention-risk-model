"""Empaqueta artefactos ligeros para el tablero institucional.

El CSV de secciones pesa ~28 MB; el tablero no debe cargarlo completo.
Este script genera resúmenes JSON por entidad y por municipio, más un
recorte de validación, para que vocales y DECEYEC abran la herramienta
sin esperar descargas pesadas.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "dashboard"


def _num(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number != number:  # NaN
        return None
    return number


def _boolish(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "si", "sí"}


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


def empaquetar_validacion() -> None:
    path = ROOT / "outputs" / "resultadosIntegrados" / "ccpc_municipioResultadosIntegrados.csv"
    points = []
    worst = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            real = _num(row.get("latest_abstention"))
            pred = _num(row.get("predicted_abstention"))
            base = _num(row.get("predicted_abstention_baseline"))
            rf = _num(row.get("predicted_abstention_random_forest"))
            err = _num(row.get("random_forest_absolute_error"))
            if real is None:
                continue
            item = {
                "entidad": row.get("EDONOM"),
                "municipio": row.get("MPIONOM"),
                "real": real,
                "pred": pred,
                "baseline": base,
                "rf": rf,
                "error": err if err is not None else (abs(rf - real) if rf is not None else None),
            }
            points.append(item)
            if item["error"] is not None:
                worst.append(item)
    worst.sort(key=lambda item: item["error"], reverse=True)
    step = max(1, len(points) // 700)
    write_json(
        OUT / "validacionMunicipio.json",
        {
            "sample": points[::step][:700],
            "zonasMayorError": worst[:25],
            "nObservaciones": len(points),
        },
    )


def empaquetar_historico_municipal() -> None:
    path = ROOT / "outputs" / "datosAnaliticos" / "ccpc_municipioAnio.csv"
    series = {}
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = f"{row['EDOCVE']}|{row['MPIOCVE']}"
            year = str(row["AELEC"])
            series.setdefault(key, {"entidad": row["EDONOM"], "municipio": row["MPIONOM"], "anios": {}})
            series[key]["anios"][year] = {
                "p": _num(row.get("participation_rate")),
                "a": _num(row.get("abstention_rate")),
                "ln": _num(row.get("LN")),
            }
    write_json(OUT / "historicoMunicipal.json", series)


def empaquetar_secciones() -> None:
    path = ROOT / "outputs" / "resultadosIntegrados" / "ccpc_seccionResultadosIntegrados.csv"
    por_entidad = defaultdict(list)
    por_municipio = defaultdict(lambda: {"total": 0, "alto": 0, "medio": 0, "bajo": 0, "sin_historico": 0, "top": []})
    ranking_nacional = []

    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            level = str(row.get("risk_level") or "").strip().lower()
            if level not in {"alto", "medio", "bajo"}:
                level = "sin_historico"
            slim = {
                "edo": row.get("EDONOM"),
                "edocve": row.get("EDOCVE"),
                "mpio": row.get("MPIONOM"),
                "mpiocve": row.get("MPIOCVE"),
                "seccion": row.get("SECCION"),
                "tipo": row.get("TIPOSEC"),
                "p": _num(row.get("latest_participation")),
                "a": _num(row.get("latest_abstention")),
                "slope": _num(row.get("participation_slope")),
                "vol": _num(row.get("latest_participation_volatility_3")),
                "risk": _num(row.get("risk_score")),
                "level": level,
                "reason": row.get("risk_reason") or "",
                "ln": _num(row.get("latest_ln")),
                "reliable": _boolish(row.get("trend_reliable")),
            }
            por_entidad[row.get("EDOCVE") or "00"].append(slim)
            mkey = f"{row.get('EDOCVE')}|{row.get('MPIOCVE')}"
            bucket = por_municipio[mkey]
            bucket["total"] += 1
            bucket[level] = bucket.get(level, 0) + 1
            bucket["entidad"] = row.get("EDONOM")
            bucket["municipio"] = row.get("MPIONOM")
            if slim["risk"] is not None:
                bucket["top"].append(dict(slim))
                ranking_nacional.append(slim)

    for mkey, bucket in por_municipio.items():
        bucket["top"] = sorted(
            bucket["top"],
            key=lambda item: item["risk"] if item["risk"] is not None else -1,
            reverse=True,
        )[:8]
        for item in bucket["top"]:
            item.pop("edo", None)
            item.pop("mpio", None)

    ranking_nacional.sort(key=lambda item: item["risk"] if item["risk"] is not None else -1, reverse=True)

    write_json(OUT / "seccionesPorMunicipio.json", por_municipio)
    write_json(OUT / "topSeccionesNacional.json", ranking_nacional[:200])

    dest = OUT / "secciones"
    dest.mkdir(parents=True, exist_ok=True)
    index = {}
    for edocve, rows in por_entidad.items():
        write_json(dest / f"{edocve}.json", rows)
        index[edocve] = {
            "n": len(rows),
            "entidad": rows[0]["edo"] if rows else "",
        }
    write_json(OUT / "indiceSeccionesEntidad.json", index)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    empaquetar_validacion()
    empaquetar_historico_municipal()
    empaquetar_secciones()
    print("Dashboard data pack ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
