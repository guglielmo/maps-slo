# maps/ — application to the Italian municipalities (MAPS)

Not part of the installable package. Run once, in order:

1. `maps/prepare/convert.py` — GSSI `.dta` (zip of 16/10/2026) → Parquet in `maps/data/`
2. ISTAT resident population on 1 January 2025 (demo.istat.it, also in the MAPS Datastore)
   → `maps/data/population-2025.csv` with columns `id`, `name`, `population`
3. `maps/prepare/build_units.py` — units = population + GSSI levels
4. `maps/prepare/fusions_draft.py`, then complete `maps/reference/fusions-2021-2025.csv` by hand
5. `maps/prepare/reconduct.py` — 2021 matrix → 2025 codes (decision D10)
6. `maps-slo run maps/scenarios/maps-2025.yaml --out output/maps-2025 --manifest-extra maps/data/reconduction.json`
7. a second run to `output/maps-2025-bis` and one of `maps/scenarios/maps-2025-d30.yaml` to
   `output/maps-2025-d30`, then `python maps/checks.py output/maps-2025 maps/data/units-2025.parquet
   --reference-run output/maps-2025-bis --variant-run output/maps-2025-d30`
8. phase 1 against GSSI: `python maps/levels_gssi.py maps/data/levels-gssi.parquet
   maps/levels/maps-rules.yaml output/levels-gssi`
9. downstream corrections (decision D18): `python maps/corrections.py output/maps-2025
   maps/reference/corrections.csv maps/data/units-2025.parquet --out output/maps-2025-corrected`
   (the list names municipalities, so it applies to any run; outcome in `corrections.json`)
10. GeoJSON for mapshaper.org or a GIS: download the ISTAT boundaries of 1 January 2025
   (generalised, `Limiti01012025_g.zip`) into `maps/data/istat-limiti-2025/`, then
   `python maps/geo_export.py output/maps-2025-corrected maps/data/istat-limiti-2025/Com01012025_g/Com01012025_g_WGS84.shp
   --times maps/data/times-2025.parquet --units-input maps/data/units-2025.parquet`
   → `output/maps-2025-corrected/geo/comuni.geojson` and `sistemi.geojson`
11. calibration grid (D3.3.2 method draft): `python maps/calibrate.py maps/calibration/grid-2025.yaml
    --out output/calibration-2025` → one row per combination of the grid with the measures
    of the draft, plus the system of every unit for every combination (`roots.npz`)
12. levels by phase 1 (decision D16) on the GSSI services file of 5/11/2026:
    `python maps/prepare/services_gssi.py maps/data/file_prova_algoritmo_modulo_1.xlsx
    maps/data/services-2025.csv` (`--health hospital` for hospitals only), then
    `maps-slo levels maps/levels/maps-rules.yaml maps/data/services-2025.csv --out output/levels-d16/levels.parquet`,
    `python maps/prepare/build_units.py maps/data/population-2025.csv output/levels-d16/levels.parquet
    maps/data/units-2025-d16.parquet` and `maps-slo run maps/scenarios/maps-2025-d16.yaml --out output/maps-2025-d16`

`maps/data/` is not versioned. The GSSI data (Stata routine and input files of 16/10/2026) are provided by GSSI and are not redistributed here.
