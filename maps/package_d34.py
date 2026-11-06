"""Package of the MAPS deliverable D3.4 (national SLO dataset and metadata) from a corrected run.

    python maps/package_d34.py output/d34-v1.0/corrected output/d34-v1.0/corrected/geo \
        --version 1.0 --units-input maps/data/units-2025-d16.parquet \
        --services maps/data/services-2025.csv --out output/D3.4-SLO-2025-v1.0

Layout of the package (the README in Italian, maps/reference/d34/LEGGIMI.md, describes it):

- sistemi.gpkg, comuni.gpkg — one polygon per system, one per municipality
- sistemi.geojson, comuni.geojson — the same layers, for the web
- sistemi.csv, comuni.csv — the same attributes without geometry
- metadati/ — manifest, scenario, metrics of the algorithm, outcome of the corrections,
  description of the fields
- ingresso/ — the inputs of the run that can be redistributed: units with population and
  levels, phase-1 attributes from the GSSI services file, corrections, fusions 2021-2025.
  The travel-time matrix (ISTAT on TomTom graph) is NOT included.
- SHA256SUMS — checksums of every file of the package
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).parent
REFERENCE = HERE / "reference"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path, help="corrected run (output of maps/corrections.py)")
    ap.add_argument("geo", type=Path, help="output of maps/geo_export.py for that run")
    ap.add_argument("--version", required=True)
    ap.add_argument("--units-input", type=Path, required=True)
    ap.add_argument("--services", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    out = a.out
    if out.exists():
        shutil.rmtree(out)
    (out / "metadati").mkdir(parents=True)
    (out / "ingresso").mkdir()

    con = duckdb.connect()
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute("SET geometry_always_xy = true")

    for layer in ("sistemi", "comuni"):
        src = a.geo / f"{layer}.geojson"
        shutil.copy(src, out / src.name)
        con.execute(f"CREATE TABLE {layer} AS SELECT COLUMNS(lambda c: c != 'OGC_FID') FROM ST_Read('{src}')")
        # one GeoPackage per layer: the GDAL writer of DuckDB creates a new file at every COPY
        gpkg = out / f"{layer}.gpkg"
        con.execute(
            f"""COPY {layer} TO '{gpkg}' (FORMAT GDAL, DRIVER 'GPKG', LAYER_NAME '{layer}',
                SRS 'EPSG:4326')"""
        )
        con.execute(
            f"COPY (SELECT * EXCLUDE (geom) FROM {layer} ORDER BY 1) TO '{out / f'{layer}.csv'}' (HEADER)"
        )
    for layer in ("sistemi", "comuni"):
        gpkg = out / f"{layer}.gpkg"
        n_gpkg = con.execute(f"SELECT count(*) FROM ST_Read('{gpkg}')").fetchone()[0]
        n_src = con.execute(f"SELECT count(*) FROM {layer}").fetchone()[0]
        if n_gpkg != n_src:
            raise SystemExit(f"GeoPackage layer {layer}: {n_gpkg} rows, expected {n_src}")

    for name in ("manifest.json", "scenario.yaml", "metrics.json", "corrections.json"):
        shutil.copy(a.run / name, out / "metadati" / name)
    shutil.copy(REFERENCE / "d34" / "campi.md", out / "metadati" / "campi.md")

    units = pd.read_parquet(a.units_input)
    units.to_csv(out / "ingresso" / "comuni-livelli-popolazione.csv", index=False)
    shutil.copy(a.services, out / "ingresso" / "servizi-2025.csv")
    shutil.copy(REFERENCE / "corrections.csv", out / "ingresso" / "correzioni.csv")
    shutil.copy(REFERENCE / "fusions-2021-2025.csv", out / "ingresso" / "fusioni-2021-2025.csv")

    readme = (REFERENCE / "d34" / "LEGGIMI.md").read_text()
    (out / "LEGGIMI.md").write_text(readme.replace("{version}", a.version))
    shutil.copy(REFERENCE / "d34" / "LICENZA-DATI.md", out / "LICENZA-DATI.md")

    files = sorted(p for p in out.rglob("*") if p.is_file())
    (out / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(out)}\n" for p in files)
    )
    manifest = json.loads((a.run / "manifest.json").read_text())
    print(f"{out}: {len(files)} files, code {manifest.get('git_commit')}")


if __name__ == "__main__":
    main()
