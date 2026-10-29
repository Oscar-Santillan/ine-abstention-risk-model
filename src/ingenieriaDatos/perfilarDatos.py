"""Perfila los datasets CCPC agregados y escribe un reporte reproducible de calidad."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = (
    "AELEC",
    "FELECCION",
    "EDOCVE",
    "EDONOM",
    "MPIOCVE",
    "MPIONOM",
    "SECCION",
    "TIPOSEC",
    "DEF",
    "DEL",
    "SEXO",
    "EDAD",
    "LN",
    "SV",
    "NV",
    "NS",
)
COUNT_COLUMNS = ("LN", "SV", "NV", "NS")
EXPECTED_YEARS = ("2009", "2012", "2015", "2018", "2021", "2024")


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def perfilarArchivo(path: Path, chunksize: int) -> dict[str, object]:
    stats: dict[str, object] = {
        "file": path.name,
        "bytes": path.stat().st_size,
        "rows": 0,
        "columns": [],
        "missing": {column: 0 for column in REQUIRED_COLUMNS},
        "min": {},
        "max": {},
        "sums": {column: 0 for column in COUNT_COLUMNS},
        "unique": {column: set() for column in ("AELEC", "EDOCVE", "TIPOSEC", "SEXO")},
        "dates": set(),
        "balance_violations": 0,
        "negative_violations": 0,
        "rate_violations": 0,
    }
    started = time.time()

    try:
        reader = pd.read_csv(
            path,
            encoding="utf-8-sig",
            chunksize=chunksize,
            low_memory=False,
        )
        for chunk_index, chunk in enumerate(reader):
            if chunk_index == 0:
                columns = [str(column).strip().lstrip("\ufeff") for column in chunk.columns]
                stats["columns"] = columns
                missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
                if missing_columns:
                    raise ValueError(f"Faltan columnas en {path}: {', '.join(missing_columns)}")

            stats["rows"] = int(stats["rows"]) + len(chunk)
            missing = stats["missing"]
            for column in REQUIRED_COLUMNS:
                missing[column] += int(chunk[column].isna().sum())

            unique = stats["unique"]
            for column in unique:
                unique[column].update(str(value) for value in chunk[column].dropna().unique())
            stats["dates"].update(str(value) for value in chunk["FELECCION"].dropna().unique())

            numeric = chunk[list(COUNT_COLUMNS)].apply(pd.to_numeric, errors="coerce")
            for column in COUNT_COLUMNS:
                series = numeric[column]
                stats["sums"][column] += float(series.sum())
                minimum, maximum = series.min(), series.max()
                if pd.notna(minimum):
                    stats["min"][column] = min(
                        stats["min"].get(column, float("inf")), float(minimum)
                    )
                if pd.notna(maximum):
                    stats["max"][column] = max(
                        stats["max"].get(column, float("-inf")), float(maximum)
                    )

            age = pd.to_numeric(chunk["EDAD"], errors="coerce")
            stats["min"]["EDAD"] = min(stats["min"].get("EDAD", float("inf")), float(age.min()))
            stats["max"]["EDAD"] = max(stats["max"].get("EDAD", float("-inf")), float(age.max()))
            stats["negative_violations"] += int((numeric < 0).any(axis=1).sum())
            stats["balance_violations"] += int(
                (numeric["SV"] + numeric["NV"] + numeric["NS"] != numeric["LN"]).sum()
            )
            stats["rate_violations"] += int(
                numeric[list(("SV", "NV", "NS"))].gt(numeric["LN"], axis=0).any(axis=1).sum()
            )
    except (OSError, UnicodeError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise RuntimeError(f"Error perfilando {path}: {error}") from error

    stats["unique"] = {key: sorted(values) for key, values in stats["unique"].items()}
    stats["dates"] = sorted(stats["dates"])
    stats["duration_seconds"] = round(time.time() - started, 1)
    return stats


def interpretarArgumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = obtenerRaizProyecto()
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=root / "data" / "processed",
        help="Directorio con los CSV agregados.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "outputs" / "datosAnaliticos" / "manifiestoPerfilado.json",
        help="Ruta del reporte JSON.",
    )
    parser.add_argument("--chunksize", type=int, default=200_000)
    return parser.parse_args()


def main() -> int:
    args = interpretarArgumentos()
    if args.chunksize <= 0:
        raise ValueError("chunksize debe ser mayor que cero")

    files = sorted(args.processed_root.glob("ccpc_*_aggregated.csv"))
    if not files:
        raise FileNotFoundError(f"No se encontraron datasets en {args.processed_root}")

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "files": [],
        "cross_year": {
            "expected_years": list(EXPECTED_YEARS),
            "file_count": len(files),
        },
    }
    for path in files:
        stats = perfilarArchivo(path, args.chunksize)
        report["files"].append(stats)
        print(f"{path.name}: {stats['rows']:,} filas")

    years = [
        file_stats["unique"]["AELEC"][0]
        for file_stats in report["files"]
        if file_stats["unique"]["AELEC"]
    ]
    report["cross_year"]["years"] = years
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
