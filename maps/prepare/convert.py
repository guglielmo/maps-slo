"""Convert the GSSI Stata files (zip of 16/10/2026) to Parquet.

    python maps/prepare/convert.py maps/data/gssi maps/data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def code(s: pd.Series) -> pd.Series:
    return s.astype("int64").astype(str).str.zfill(6)


def convert_times(src: Path, dst: Path, chunksize: int = 5_000_000) -> int:
    """distanze_2021.dta -> origin, destination (2021 ISTAT codes, int), minutes (ttp_tot,
    free-flow, decision D17). tep_tot and km_tot are dropped."""
    schema = pa.schema([("origin", pa.int32()), ("destination", pa.int32()),
                        ("minutes", pa.int16())])
    n = 0
    with pq.ParquetWriter(dst, schema) as writer, pd.read_stata(
        src, columns=["cod_istat_or", "cod_istat_dest", "ttp_tot"], chunksize=chunksize,
        convert_categoricals=False,
    ) as reader:
        for chunk in reader:
            t = chunk["ttp_tot"]
            if (t != t.round()).any():
                raise SystemExit("ttp_tot has fractional minutes: the int16 cast would truncate")
            table = pa.table({
                "origin": chunk["cod_istat_or"].astype("int32"),
                "destination": chunk["cod_istat_dest"].astype("int32"),
                "minutes": chunk["ttp_tot"].astype("int16"),
            }, schema=schema)
            writer.write_table(table)
            n += len(chunk)
    return n


def convert_contiguity(src: Path, dst: Path) -> int:
    df = pd.read_stata(src)
    df = df.dropna(subset=["PRO_COM_N", "PRO_COM_A"])  # two empty trailing rows in the file
    out = pd.DataFrame({
        "origin": code(df["PRO_COM_N"]),
        "neighbour": code(df["PRO_COM_A"]),
        "origin_name": df["COMUNE"].astype(str),
        "shared_length": df["lunghezza_km"].astype("float64"),
        "origin_perimeter": df["lunghezza_km_tot"].astype("float64"),
    })
    out.to_parquet(dst, index=False)
    return len(out)


def convert_levels(src: Path, dst: Path) -> int:
    df = pd.read_stata(src)
    out = pd.DataFrame({
        "id": code(df["PRO_COM"]),
        "name": df["Comune"].astype(str),
        "level": df["centralità"].astype("Int64"),
        "gssi_tier": df["tutto"].astype(str),
        "population": df["Pop_1125"].astype("int64"),
        "n_health": df["NUM_OSPEDALI"],
        "n_dea": df["NUM_DEA"],
        "pnrr_m6": pd.to_numeric(df["PNRR_Missione6"], errors="coerce"),
        "n_school_types": df["conta_tipi_scuoleSUP"],
        "snai_school_index": df["IND_scuoleSUP_snai"],
        "station_category": df["Stazioni_max_METALLI"].astype(str).str.strip().str.lower()
        .replace({"": None, "nan": None, "#n/a": None}),
    })
    out.to_parquet(dst, index=False)
    return len(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    a = ap.parse_args()
    a.dst.mkdir(parents=True, exist_ok=True)
    print("contiguity", convert_contiguity(a.src / "comuni_matrice_contiguità.dta",
                                           a.dst / "contiguity-2025.parquet"))
    print("levels", convert_levels(a.src / "centralità.dta", a.dst / "levels-gssi.parquet"))
    print("times", convert_times(a.src / "distanze_2021.dta", a.dst / "times-2021.parquet"))


if __name__ == "__main__":
    main()
