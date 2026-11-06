# Homogeneous Local Systems 2025 — national dataset, version {version}

Deliverable D3.4 of the MAPS project (Multidimensional Area Place-based System, FRES 2 call, CUP B13C25001430001): national geospatial dataset of the Homogeneous Local Systems (*Sistemi Locali Omogenei*, SLO) and associated metadata.

## What this version is

The **reference run** of the SLO algorithm on the Italian municipalities of 2025, produced with the «maps-slo» library (deliverable D3.5), which implements the specification of the algorithm agreed with GSSI (D3.2.1, appendix A1, decisions D1-D26) and is verified against the D3.2.1 criteria.

Version {version} is complete: it covers every Italian municipality of 2025, with the metadata and the inputs needed to regenerate it. The aggregation parameters come from the calibration method of the D3.3.2; the definitions of the services used for the levels follow decision D16 on the data provided by GSSI on 5 November 2026. GST and GSSI, with their developers and experts, can change and maintain library, parameters and inputs as they need: the dataset is regenerated with the commands under «How to regenerate», with no change to the code when only parameters or data change, and every new run is a new version.

## Contents

| File | Content |
|---|---|
| `sistemi.gpkg`, `sistemi.geojson` | one polygon per local system (union of the ISTAT 2025 municipal boundaries), with the measures as attributes |
| `comuni.gpkg`, `comuni.geojson` | one polygon per municipality, with its system and how it got there |
| `sistemi.csv`, `comuni.csv` | the same attributes, without geometry |
| `metadata/manifest.json` | code version, parameters, fingerprint of every input, machine and software of the run |
| `metadata/scenario.yaml` | the parameters of the run |
| `metadata/metrics.json` | the measures of the algorithm (V2-V10 of the D3.2.1), before the downstream corrections |
| `metadata/corrections.json` | the outcome of every downstream correction (decision D18) |
| `metadata/FIELDS.md` | the description of the fields |
| `input/` | the redistributable inputs: municipalities with population and level, service attributes, corrections, municipal fusions 2021-2025 |
| `SHA256SUMS` | the fingerprint of every file of the package |

Reference system: WGS84 (EPSG:4326). Municipality codes: six-digit ISTAT code (`PRO_COM_T`), boundaries at 1 January 2025. File names (`sistemi`, `comuni`) are the Italian words for systems and municipalities.

## This version in numbers

- 7,896 municipalities, all assigned to a system;
- 934 systems after the downstream corrections (936 out of the algorithm), 16 of them made of a single municipality;
- 3 distant municipalities, beyond 60 minutes from the nearest centre (Capraia Isola, Ponza, Ventotene);
- time threshold for the phase-2 unions: 31 minutes, with a minimum shared border of 3.09%.

## Points GST and GSSI may revise

- **Calibration.** The parameters come from the D3.3.2 calibration method, submitted to GSSI for validation. The minimum of the cost function is shallow between 26 and 31 minutes: a different threshold in that range is defensible.
- **Levels.** The levels follow decision D16 on the GSSI services data. To be confirmed with GSSI: the PNRR community houses as health facilities (with them, 1,259 centralities; without, 847), the number of school types read as number of schools, the classification of the RFI stations, the date of the population.
- **Municipalities without travel times.** Misiliscemi (created in 2021, absent from the 2021 matrix) is assigned to Trapani; the Isole Tremiti, with no road link, are a single-municipality system. Both are downstream corrections, listed in `input/corrections.csv`.
- **Schema of the WP2 attractors table** (decision D9): not yet defined, so the dataset is not yet in the schema of the MAPS Datastore.

## Data not included

The **travel-time matrix** (ISTAT, on TomTom graph, 2021 municipalities reconducted to 2025 by decision D10) is needed to regenerate the dataset but is not included: its licence must be cleared with ISTAT before any redistribution. The manifest records its fingerprint, so whoever holds it can check they use the same one. For the same reason the files of the GSSI Stata routine are not included.

## How to regenerate

From the library repository, with the travel-time matrix in `maps/data/`:

```
maps-slo run maps/scenarios/maps-2025-d16-cost-agreed.yaml --out <dir>/run --manifest-extra maps/data/reconduction.json
python maps/corrections.py <dir>/run maps/reference/corrections.csv maps/data/units-2025-d16.parquet --out <dir>/corrected
python maps/geo_export.py <dir>/corrected <ISTAT 2025 boundaries> --times maps/data/times-2025.parquet --units-input maps/data/units-2025-d16.parquet
python maps/package_d34.py <dir>/corrected <dir>/corrected/geo --version <version> --units-input maps/data/units-2025-d16.parquet --services maps/data/services-2025.csv --out <package>
```

To change the calibration, edit `contiguity` and `distant_minutes` in the scenario; to change the definitions of the levels, `maps/levels/maps-rules.yaml`. Complete instructions in `maps/README.md` of the repository.

## Sources

- Municipal boundaries: ISTAT, «Limiti amministrativi» at 1 January 2025, generalised version.
- Resident population: ISTAT, 1 January 2025.
- Travel-time matrix: ISTAT, on TomTom graph (not included).
- Service attributes (health facilities, emergency departments, PNRR community houses, upper-secondary schools, RFI stations): GSSI file of 5 November 2026.
- Algorithm: specification agreed between the consultant, GST and GSSI (D3.2.1, appendix A1), implemented in the «maps-slo» library.
