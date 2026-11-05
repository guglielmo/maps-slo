"""GeoJSON of a national run, for mapshaper.org or any GIS.

    python maps/geo_export.py output/maps-2025 \
        maps/data/istat-limiti-2025/Com01012025_g/Com01012025_g_WGS84.shp

Boundaries: ISTAT, "Limiti amministrativi" of 1 January 2025, generalised version
(https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2025/Limiti01012025_g.zip).

Writes in <run>/geo/:
- comuni.geojson — one feature per municipality, with its row of the units table;
- sistemi.geojson — one feature per system, the union of its municipalities;
- both with `color`, a small integer such that two adjacent systems never share it;
- with `--times`: `minutes_to_centre` per municipality (0 for the main centre), and per
  system the maximum and the mean (population-weighted with `--units-input`).

Geometry stays out of the maps_sll package: this is a MAPS presentation step.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

PRECISION = 5  # decimal degrees, about one metre


def greedy_colors(con: duckdb.DuckDBPyConnection) -> None:
    """Colour the systems so that adjacent systems differ (largest systems first)."""
    pairs = con.execute(
        """SELECT DISTINCT a.system_id, b.system_id FROM com a JOIN com b
           ON a.system_id < b.system_id AND ST_Intersects(a.geom, b.geom)"""
    ).fetchall()
    order = [s for (s,) in con.execute(
        "SELECT system_id FROM sys ORDER BY n_units DESC, system_id").fetchall()]
    adj: dict[str, set[str]] = {s: set() for s in order}
    for a, b in pairs:
        adj[a].add(b)
        adj[b].add(a)
    color: dict[str, int] = {}
    for s in order:
        used = {color[n] for n in adj[s] if n in color}
        color[s] = next(c for c in range(len(order)) if c not in used)
    con.execute("CREATE TABLE colors (system_id VARCHAR, color INTEGER)")
    con.executemany("INSERT INTO colors VALUES (?, ?)", list(color.items()))
    print(f"{len(pairs)} adjacent system pairs, {max(color.values()) + 1} colours")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path, help="output directory of `maps-sll run`")
    ap.add_argument("boundaries", type=Path, help="ISTAT municipalities shapefile (EPSG:32632)")
    ap.add_argument("--out", type=Path, help="default: <run>/geo")
    ap.add_argument("--times", type=Path,
                    help="travel-time matrix of the run: adds the minutes to the main centre")
    ap.add_argument("--units-input", type=Path,
                    help="units file of the run (weights): adds the weighted mean per system")
    a = ap.parse_args()
    out = a.out or a.run / "geo"
    out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute(f"CREATE TABLE units AS SELECT * FROM read_parquet('{a.run / 'units.parquet'}')")
    con.execute(f"CREATE TABLE unassigned AS SELECT * FROM read_parquet('{a.run / 'unassigned.parquet'}')")
    con.execute(f"CREATE TABLE sys AS SELECT * FROM read_parquet('{a.run / 'systems.parquet'}')")
    con.execute(
        f"""CREATE TABLE shp AS SELECT PRO_COM_T AS id, COMUNE AS istat_name,
                   lpad(CAST(COD_REG AS VARCHAR), 2, '0') AS cod_reg,
                   lpad(CAST(COD_UTS AS VARCHAR), 3, '0') AS cod_uts,
                   ST_MakeValid(ST_Transform(geom, 'EPSG:32632', 'EPSG:4326', always_xy := true)) AS geom
            FROM ST_Read('{a.boundaries}')"""
    )
    missing = con.execute(
        "SELECT id FROM units WHERE id NOT IN (SELECT id FROM shp) "
        "UNION ALL SELECT id FROM unassigned WHERE id NOT IN (SELECT id FROM shp)"
    ).fetchall()
    if missing:
        raise SystemExit(f"municipalities of the run without boundaries: {[i for (i,) in missing][:20]}")
    (extra,) = con.execute(
        "SELECT count(*) FROM shp WHERE id NOT IN (SELECT id FROM units UNION SELECT id FROM unassigned)"
    ).fetchall()[0]
    if extra:
        print(f"warning: {extra} boundaries without a row in the run (left out)")

    con.execute(
        """CREATE TABLE com AS
           SELECT s.id, coalesce(u.name, n.name) AS name, s.cod_reg, s.cod_uts,
                  u.system_id, u.system_name, u.full_label, u.role, u.level,
                  u.direct_step_id, d.name AS direct_step_name, u.minutes, u.distant,
                  u.phase, u.rule, u.chain, CAST(u.missing AS VARCHAR) AS missing,
                  (n.id IS NOT NULL) AS unassigned, s.geom
           FROM shp s
           LEFT JOIN units u ON u.id = s.id
           LEFT JOIN unassigned n ON n.id = s.id
           LEFT JOIN units d ON d.id = u.direct_step_id
           WHERE u.id IS NOT NULL OR n.id IS NOT NULL"""
    )
    if a.times:
        # direction of the run: origin = the unit, destination = the centrality
        con.execute(
            f"""ALTER TABLE com ADD COLUMN minutes_to_centre DOUBLE;
                UPDATE com SET minutes_to_centre = CASE WHEN com.id = com.system_id THEN 0
                                                        ELSE t.minutes END
                FROM (SELECT lpad(CAST(origin AS VARCHAR), 6, '0') AS o,
                             lpad(CAST(destination AS VARCHAR), 6, '0') AS d, minutes
                      FROM read_parquet('{a.times}')) t
                WHERE t.o = com.id AND t.d = com.system_id"""
        )
        con.execute("UPDATE com SET minutes_to_centre = 0 WHERE id = system_id")
        weight = "1.0"
        if a.units_input:
            con.execute(f"CREATE TABLE w AS SELECT id, weight FROM read_parquet('{a.units_input}')")
            weight = "(SELECT weight FROM w WHERE w.id = com.id)"
        con.execute(
            f"""CREATE TABLE sys_minutes AS SELECT system_id,
                       max(minutes_to_centre) AS max_minutes_to_centre,
                       round(sum({weight} * minutes_to_centre) / sum({weight}), 1)
                           AS mean_minutes_to_centre
                FROM com WHERE system_id IS NOT NULL AND minutes_to_centre IS NOT NULL
                GROUP BY 1"""
        )
        (n_missing,) = con.execute(
            "SELECT count(*) FROM com WHERE system_id IS NOT NULL AND minutes_to_centre IS NULL"
        ).fetchall()[0]
        if n_missing:
            print(f"warning: {n_missing} assigned municipalities without a time to their centre")
    else:
        con.execute("CREATE TABLE sys_minutes AS SELECT system_id FROM sys")
    greedy_colors(con)

    opts = f"(FORMAT GDAL, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS ('RFC7946=YES', 'COORDINATE_PRECISION={PRECISION}'))"
    comuni = out / "comuni.geojson"
    con.execute(
        f"""COPY (SELECT c.* EXCLUDE (geom), k.color, c.geom FROM com c
                  LEFT JOIN colors k USING (system_id) ORDER BY c.id) TO '{comuni}' {opts}"""
    )
    sistemi = out / "sistemi.geojson"
    con.execute(
        f"""COPY (SELECT s.*, m.* EXCLUDE (system_id), k.color, g.geom FROM sys s
                  LEFT JOIN sys_minutes m USING (system_id)
                  JOIN (SELECT system_id, ST_Union_Agg(geom) AS geom FROM com
                        WHERE system_id IS NOT NULL GROUP BY 1) g USING (system_id)
                  JOIN colors k USING (system_id) ORDER BY s.system_id) TO '{sistemi}' {opts}"""
    )
    for f in (comuni, sistemi):
        print(f"{f}: {f.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
