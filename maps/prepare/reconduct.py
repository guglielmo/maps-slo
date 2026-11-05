"""Reconduct the 2021 travel-time matrix to the 2025 municipalities (decision D10, R6).

    python maps/prepare/reconduct.py maps/data/times-2021.parquet \
        maps/reference/fusions-2021-2025.csv maps/data/units-2025.parquet maps/data
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

MAPPED = """
SELECT coalesce(fo.code_2025, t.o) AS origin,
       coalesce(fd.code_2025, t.d) AS destination,
       t.minutes
FROM (SELECT lpad(CAST(origin AS VARCHAR), 6, '0') AS o,
             lpad(CAST(destination AS VARCHAR), 6, '0') AS d, minutes
      FROM read_parquet('{times}')) t
LEFT JOIN fus fo ON fo.code_2021 = t.o
LEFT JOIN fus fd ON fd.code_2021 = t.d
WHERE coalesce(fo.is_seat, true) AND coalesce(fd.is_seat, true)
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("times", type=Path)
    ap.add_argument("fusions", type=Path)
    ap.add_argument("units", type=Path)
    ap.add_argument("out_dir", type=Path)
    a = ap.parse_args()
    con = duckdb.connect()
    con.execute(
        f"""CREATE TABLE fus AS SELECT code_2021, code_2025,
            lower(trim(is_seat)) AS seat_raw,
            coalesce(lower(trim(is_seat)) IN ('true', '1', 'yes'), false) AS is_seat, note
            FROM read_csv('{a.fusions}', all_varchar = true)"""
    )
    bad = con.execute(
        "SELECT code_2021 FROM fus WHERE seat_raw IS NULL OR seat_raw NOT IN "
        "('true', '1', 'yes', 'false', '0', 'no')"
    ).fetchall()
    if bad:
        raise SystemExit(f"is_seat must be true or false: {[c for (c,) in bad]}")
    incomplete = con.execute(
        "SELECT code_2021 FROM fus WHERE code_2025 IS NULL OR code_2025 = ''"
    ).fetchall()
    if incomplete:
        raise SystemExit(f"fusions table incomplete: {[c for (c,) in incomplete]}")
    # A merger needs exactly one seat. An incorporation needs none: the incorporating
    # municipality keeps its code, is already in the 2021 matrix and is not listed.
    seats = con.execute(
        f"""SELECT code_2025, n FROM (
                SELECT code_2025, count(*) FILTER (WHERE is_seat) AS n FROM fus GROUP BY 1)
            WHERE NOT (n = 1 OR (n = 0 AND code_2025 IN (
                SELECT DISTINCT lpad(CAST(origin AS VARCHAR), 6, '0')
                FROM read_parquet('{a.times}')
                EXCEPT SELECT code_2021 FROM fus)))"""
    ).fetchall()
    if seats:
        raise SystemExit(f"every merger needs exactly one seat: {seats}")
    con.execute(f"CREATE TABLE units AS SELECT id FROM read_parquet('{a.units}')")
    mapped = MAPPED.format(times=a.times)
    outside = con.execute(
        f"SELECT DISTINCT origin FROM ({mapped}) WHERE origin NOT IN (SELECT id FROM units)"
    ).fetchall()
    outside += con.execute(
        f"SELECT DISTINCT destination FROM ({mapped}) "
        "WHERE destination NOT IN (SELECT id FROM units)"
    ).fetchall()
    outside = sorted(set(outside))
    if outside:
        raise SystemExit(f"2021 codes neither in the 2025 units nor in the fusions table: "
                         f"{[c for (c,) in outside][:20]}")
    dup = con.execute(
        f"SELECT count(*) FROM (SELECT origin, destination FROM ({mapped}) "
        "GROUP BY 1, 2 HAVING count(*) > 1)"
    ).fetchone()[0]
    if dup:
        raise SystemExit(f"{dup} duplicated pairs after the reconduction")
    out = a.out_dir / "times-2025.parquet"
    con.execute(f"COPY ({mapped} ORDER BY 1, 2) TO '{out}' (FORMAT parquet)")
    con.execute(f"COPY (SELECT code_2021, code_2025, is_seat AS kept, note FROM fus ORDER BY 1) "
                f"TO '{a.out_dir / 'reconducted.csv'}' (HEADER)")
    without = [c for (c,) in con.execute(
        f"SELECT id FROM units EXCEPT SELECT DISTINCT origin FROM read_parquet('{out}') ORDER BY 1"
    ).fetchall()]
    rows = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    summary = {
        "travel_time_reconduction": {
            "rule": "decision D10: the municipality hosting the town hall survives",
            "reconducted": [dict(zip(("code_2021", "code_2025", "kept"), r)) for r in
                            con.execute("SELECT code_2021, code_2025, is_seat FROM fus "
                                        "ORDER BY 1").fetchall()],
            "units_without_times": without,
            "pairs": rows,
        }
    }
    (a.out_dir / "reconduction.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{rows} pairs; units without times: {without}")


if __name__ == "__main__":
    main()
