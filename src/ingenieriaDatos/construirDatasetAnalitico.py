"""Build section-year and municipality-year datosAnaliticos CCPC tables."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import pandas as pd


YEARS = ("2009", "2012", "2015", "2018", "2021", "2024")
INPUT_COLUMNS = [
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
]
COUNT_COLUMNS = ("LN", "SV", "NV", "NS")
SEX_VALUES = ("0", "1", "2")
AGE_BANDS = ("under_30", "age_30_59", "age_60_plus")


def obtenerRaizProyecto() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_partials(path: Path, keys: list[str], chunksize: int) -> list[pd.DataFrame]:
    partials = []
    for chunk in pd.read_csv(
        path,
        usecols=INPUT_COLUMNS,
        encoding="utf-8-sig",
        chunksize=chunksize,
        low_memory=False,
    ):
        for column in COUNT_COLUMNS + ("EDAD", "SEXO"):
            chunk[column] = pd.to_numeric(chunk[column], errors="coerce")
        chunk["age_weight"] = chunk["EDAD"] * chunk["LN"]
        chunk["del_available_weight"] = chunk["LN"].where(chunk["DEL"].notna(), 0)
        chunk["sex_0_weight"] = chunk["LN"].where(chunk["SEXO"] == 0, 0)
        chunk["sex_1_weight"] = chunk["LN"].where(chunk["SEXO"] == 1, 0)
        chunk["sex_2_weight"] = chunk["LN"].where(chunk["SEXO"] == 2, 0)
        chunk["under_30_weight"] = chunk["LN"].where(chunk["EDAD"] < 30, 0)
        chunk["age_30_59_weight"] = chunk["LN"].where(chunk["EDAD"].between(30, 59), 0)
        chunk["age_60_plus_weight"] = chunk["LN"].where(chunk["EDAD"] >= 60, 0)

        aggregations = {
            column: "sum"
            for column in COUNT_COLUMNS
        }
        aggregations.update(
            {
                "age_weight": "sum",
                "del_available_weight": "sum",
                "sex_0_weight": "sum",
                "sex_1_weight": "sum",
                "sex_2_weight": "sum",
                "under_30_weight": "sum",
                "age_30_59_weight": "sum",
                "age_60_plus_weight": "sum",
            }
        )
        if "TIPOSEC" in keys:
            aggregations["DEF"] = "first"
            aggregations["DEL"] = "first"
        partials.append(chunk.groupby(keys, dropna=False, sort=False).agg(aggregations).reset_index())
    return partials


def _finalise(partials: list[pd.DataFrame], output: Path, *, include_section: bool) -> int:
    if not partials:
        raise ValueError("No se encontraron datos para agregar")
    keys = [
        "AELEC",
        "FELECCION",
        "EDOCVE",
        "EDONOM",
        "MPIOCVE",
        "MPIONOM",
    ]
    if include_section:
        keys += ["SECCION", "TIPOSEC"]
    aggregations = {
        column: "sum"
        for column in (
            COUNT_COLUMNS
            + (
                "age_weight",
                "del_available_weight",
                "sex_0_weight",
                "sex_1_weight",
                "sex_2_weight",
                "under_30_weight",
                "age_30_59_weight",
                "age_60_plus_weight",
            )
        )
    }
    if include_section:
        aggregations.update({"DEF": "first", "DEL": "first"})
    result = pd.concat(partials, ignore_index=True).groupby(
        keys, dropna=False, sort=True
    ).agg(aggregations).reset_index()
    denominator = result["LN"].replace(0, pd.NA)
    result["participation_rate"] = result["SV"] / denominator
    result["abstention_rate"] = result["NV"] / denominator
    result["non_specified_rate"] = result["NS"] / denominator
    result["average_age"] = result["age_weight"] / denominator
    result["del_available_rate"] = result["del_available_weight"] / denominator
    for sex in SEX_VALUES:
        result[f"sex_{sex}_share"] = result[f"sex_{sex}_weight"] / denominator
    for band in AGE_BANDS:
        result[f"{band}_share"] = result[f"{band}_weight"] / denominator
    drop_columns = [
        "age_weight",
        "del_available_weight",
        "sex_0_weight",
        "sex_1_weight",
        "sex_2_weight",
        "under_30_weight",
        "age_30_59_weight",
        "age_60_plus_weight",
    ]
    result = result.drop(columns=drop_columns)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=output.parent,
            prefix=f".{output.stem}_",
            suffix=".csv.tmp",
            delete=False,
        ).name
    )
    try:
        result.to_csv(temporary, index=False)
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return len(result)


def construir(processed_root: Path, output_root: Path, chunksize: int) -> tuple[int, int]:
    secciones_partials: list[pd.DataFrame] = []
    municipios_partials: list[pd.DataFrame] = []
    secciones_keys = [
        "AELEC", "FELECCION", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM",
        "SECCION", "TIPOSEC",
    ]
    municipios_keys = [
        "AELEC", "FELECCION", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM",
    ]
    for year in YEARS:
        path = processed_root / f"ccpc_{year}_aggregated.csv"
        if not path.is_file():
            raise FileNotFoundError(f"No existe el dataset: {path}")
        secciones_partials.extend(_read_partials(path, secciones_keys, chunksize))
        municipios_partials.extend(_read_partials(path, municipios_keys, chunksize))
        print(f"Procesado {year}")
    secciones_rows = _finalise(
        secciones_partials,
        output_root / "ccpc_seccionAnio.csv",
        include_section=True,
    )
    municipios_rows = _finalise(
        municipios_partials,
        output_root / "ccpc_municipioAnio.csv",
        include_section=False,
    )
    return secciones_rows, municipios_rows


def interpretarArgumentos() -> argparse.Namespace:
    root = obtenerRaizProyecto()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-root", type=Path, default=root / "data" / "processed")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "datosAnaliticos")
    parser.add_argument("--chunksize", type=int, default=200_000)
    return parser.parse_args()


def main() -> int:
    args = interpretarArgumentos()
    if args.chunksize <= 0:
        raise ValueError("chunksize debe ser mayor que cero")
    secciones_rows, municipios_rows = build(
        args.processed_root, args.output_root, args.chunksize
    )
    print(f"Secciones-año: {secciones_rows:,} filas")
    print(f"Municipios-año: {municipios_rows:,} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
