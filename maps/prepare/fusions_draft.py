"""List the codes that the 2021 matrix and the 2025 units do not share.

Writes a draft of maps/reference/fusions-2021-2025.csv to complete by hand.

    python maps/prepare/fusions_draft.py maps/data/times-2021.parquet \
        maps/data/units-2025.parquet maps/reference/fusions-2021-2025.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("times", type=Path)
    ap.add_argument("units", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    con = duckdb.connect()
    old = con.execute(
        f"""SELECT DISTINCT lpad(CAST(origin AS VARCHAR), 6, '0') AS code
            FROM read_parquet('{a.times}')
            EXCEPT SELECT id FROM read_parquet('{a.units}') ORDER BY 1"""
    ).fetchall()
    new = con.execute(
        f"""SELECT id FROM read_parquet('{a.units}')
            EXCEPT SELECT DISTINCT lpad(CAST(origin AS VARCHAR), 6, '0')
            FROM read_parquet('{a.times}') ORDER BY 1"""
    ).fetchall()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        f.write("code_2021,code_2025,is_seat,note\n")
        for (c,) in old:
            f.write(f"{c},,,\n")
    print(f"{len(old)} codes of 2021 without a 2025 match -> {a.out}")
    print(f"{len(new)} codes of 2025 without times: {[c for (c,) in new]}")


if __name__ == "__main__":
    main()
