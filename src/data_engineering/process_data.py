"""Unify the CCPC files from each election year.

The source files are split by entity and can be large enough that loading a
whole year into memory is unnecessary.  This module therefore validates the
schema and appends the files in chunks.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_YEARS = ("2009", "2012", "2015", "2018", "2021", "2024")
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


def _project_root() -> Path:
    """Return the repository root when this file is executed directly."""

    return Path(__file__).resolve().parents[2]


def _csv_files(year_dir: Path) -> list[Path]:
    """Find all source CSVs below a year's directory in stable order."""

    return sorted(
        (path for path in year_dir.rglob("*.csv") if path.is_file()),
        key=lambda path: str(path).lower(),
    )


def _normalise_columns(columns: Iterable[object]) -> list[str]:
    """Remove whitespace and a possible UTF-8 BOM from column names."""

    return [str(column).strip().lstrip("\ufeff") for column in columns]


def _validate_columns(columns: list[str], source: Path) -> None:
    expected = list(REQUIRED_COLUMNS)
    if columns != expected:
        missing = [column for column in expected if column not in columns]
        extra = [column for column in columns if column not in expected]
        details = []
        if missing:
            details.append(f"faltantes: {', '.join(missing)}")
        if extra:
            details.append(f"no esperadas: {', '.join(extra)}")
        if not details:
            details.append(f"orden esperado: {', '.join(expected)}")
        raise ValueError(f"Esquema inválido en {source}: {'; '.join(details)}")


def process_year(
    year: str | int,
    *,
    interim_root: Path | str | None = None,
    processed_root: Path | str | None = None,
    chunksize: int = 100_000,
) -> Path:
    """Unify all entity files for ``year`` and return the output path.

    Files are read in chunks to keep memory bounded.  A failed input does not
    replace an existing output because the temporary file is only moved into
    place after every source has been processed successfully.
    """

    year = str(year)
    if not year.isdigit():
        raise ValueError(f"El año debe ser numérico: {year!r}")
    if chunksize <= 0:
        raise ValueError("chunksize debe ser mayor que cero")

    root = _project_root()
    source_root = Path(interim_root) if interim_root is not None else root / "data" / "interim"
    destination_root = (
        Path(processed_root)
        if processed_root is not None
        else root / "data" / "processed"
    )
    year_dir = source_root / year
    if not year_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio de datos: {year_dir}")

    files = _csv_files(year_dir)
    if not files:
        raise FileNotFoundError(f"No se encontraron CSV para el año {year} en {year_dir}")

    destination_root.mkdir(parents=True, exist_ok=True)
    output_path = destination_root / f"ccpc_{year}_aggregated.csv"
    temporary_path: Path | None = None
    rows = 0

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination_root,
            prefix=f".ccpc_{year}_",
            suffix=".csv.tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            for file_index, source in enumerate(files):
                try:
                    reader = pd.read_csv(
                        source,
                        encoding="utf-8-sig",
                        chunksize=chunksize,
                        low_memory=False,
                    )
                    for chunk_index, chunk in enumerate(reader):
                        chunk.columns = _normalise_columns(chunk.columns)
                        _validate_columns(list(chunk.columns), source)
                        chunk.to_csv(
                            temporary,
                            index=False,
                            header=file_index == 0 and chunk_index == 0,
                        )
                        rows += len(chunk)
                except (
                    OSError,
                    UnicodeError,
                    ValueError,
                    pd.errors.EmptyDataError,
                    pd.errors.ParserError,
                ) as error:
                    raise RuntimeError(f"Error leyendo {source}: {error}") from error

        os.replace(temporary_path, output_path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    print(f"Año {year}: {len(files)} archivos, {rows:,} registros -> {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unifica los archivos CSV de CCPC por año electoral."
    )
    parser.add_argument(
        "years",
        nargs="*",
        default=list(DEFAULT_YEARS),
        help="Años a procesar (por defecto: todos los años disponibles).",
    )
    parser.add_argument(
        "--interim-root",
        type=Path,
        default=None,
        help="Directorio raíz de entrada (por defecto: data/interim).",
    )
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=None,
        help="Directorio de salida (por defecto: data/processed).",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Filas por bloque de lectura (por defecto: 100000).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        for year in args.years:
            process_year(
                year,
                interim_root=args.interim_root,
                processed_root=args.processed_root,
                chunksize=args.chunksize,
            )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Error: {error}")
        return 1
    print("Proceso de unificación anual completado con éxito.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
