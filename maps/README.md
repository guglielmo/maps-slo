# maps/ — application to the Italian municipalities (MAPS)

Not part of the installable package. Run once, in order:

1. `maps/prepare/convert.py` — GSSI `.dta` (zip of 16/10/2026) → Parquet in `maps/data/`
2. ISTAT resident population on 1 January 2025 (demo.istat.it, also in the MAPS Datastore)
   → `maps/data/population-2025.csv` with columns `id`, `name`, `population`
3. `maps/prepare/build_units.py` — units = population + GSSI levels
4. `maps/prepare/fusions_draft.py`, then complete `maps/reference/fusions-2021-2025.csv` by hand
5. `maps/prepare/reconduct.py` — 2021 matrix → 2025 codes (decision D10)
6. `maps-sll run maps/scenarios/maps-2025.yaml --out output/maps-2025 --manifest-extra maps/data/reconduction.json`
7. a second run to `output/maps-2025-bis` and one of `maps/scenarios/maps-2025-d30.yaml` to
   `output/maps-2025-d30`, then `python maps/checks.py output/maps-2025 maps/data/units-2025.parquet
   --reference-run output/maps-2025-bis --variant-run output/maps-2025-d30`
8. phase 1 against GSSI: `python maps/levels_gssi.py maps/data/levels-gssi.parquet
   maps/levels/maps-rules.yaml output/levels-gssi`
9. GeoJSON for mapshaper.org or a GIS: download the ISTAT boundaries of 1 January 2025
   (generalised, `Limiti01012025_g.zip`) into `maps/data/istat-limiti-2025/`, then
   `python maps/geo_export.py output/maps-2025 maps/data/istat-limiti-2025/Com01012025_g/Com01012025_g_WGS84.shp`
   → `output/maps-2025/geo/comuni.geojson` and `sistemi.geojson`

`maps/data/` is not versioned. The GSSI data (Stata routine and input files of 16/10/2026) are provided by GSSI and are not redistributed here.
