# Fields

## `sistemi` (systems: sistemi.gpkg, sistemi.geojson, sistemi.csv)

| Field | Description |
|---|---|
| `system_id` | ISTAT code of the municipality at the centre of the system; identifies the system |
| `name` | name of the centre |
| `main_centre_id` | code of the main centre (same as `system_id`) |
| `main_centre_level` | level of the main centre, from 1 (highest) to 6; empty for the Isole Tremiti, a system created by a downstream correction |
| `n_units` | number of municipalities in the system |
| `total_weight` | resident population of the system at 1 January 2025 |
| `merged_centres_phase2` | centralities joined to the system in phase 2 (unions by contiguity) |
| `merged_centres_phase4` | single-unit systems joined in phase 4 |
| `merged_centres_corrections` | systems joined by the downstream corrections (decision D18) |
| `max_chain_length` | largest number of union steps between centralities inside the system |
| `max_minutes_to_centre` | largest time, in minutes, from a municipality of the system to the main centre |
| `mean_minutes_to_centre` | population-weighted mean time to the main centre |
| `color` | integer from 0 to 6 such that two adjacent systems never share it, for maps |

## `comuni` (municipalities: comuni.gpkg, comuni.geojson, comuni.csv)

| Field | Description |
|---|---|
| `id` | ISTAT code of the municipality (`PRO_COM_T`) |
| `name` | name of the municipality |
| `cod_reg`, `cod_uts` | code of the region and of the supra-municipal territorial unit |
| `system_id`, `system_name` | the system it belongs to: code and name of the centre |
| `full_label` | name of the system; for a merged centrality, «centre(centrality)» |
| `role` | `main_centre` (centre of the system), `merged_centre` (centrality joined to another system), `attracted` (not a centrality) |
| `level` | level of the centrality from 1 to 6; empty for municipalities that are not centralities |
| `direct_step_id`, `direct_step_name` | the municipality it moves to directly: the nearest centrality (phase 3) or the centre a centrality joins (phases 2 and 4) |
| `minutes` | time, in minutes, to `direct_step_id` |
| `chain` | the chain of steps up to the centre of the system |
| `minutes_to_centre` | direct time, in minutes, to the centre of the system; empty for Misiliscemi, without times in the matrix |
| `distant` | `true` if the municipality is beyond the distance threshold (60 minutes) from the nearest centre |
| `phase` | phase of the algorithm that decided the assignment (2, 3 or 4); empty for municipalities assigned by a downstream correction |
| `rule` | rule applied, with the code of the specification (D3.2.1, appendix A1): `HEAD` centre, `P2-MERGE` phase-2 union, `P3-NEAREST` attraction to the nearest centrality, `P4-*` phase-4 cases |
| `missing` | missing data the outcome depends on (empty in this version) |
| `unassigned` | `true` if the municipality is in no system (none in this version) |
| `color` | the `color` of its system |

## `input/`

| File | Content |
|---|---|
| `municipalities-levels-population.csv` | per municipality: `id`, `name`, `level` (empty if not a centrality), `weight` (population at 1 January 2025); the input of the aggregation |
| `services-2025.csv` | per municipality: population and the service attributes from which phase 1 (decision D16) computes the level: `n_health` (health facilities, hospitals or PNRR community houses), `n_dea` (emergency departments), `n_secondary_schools` (upper-secondary school types), `station_category` (RFI category of the main station) |
| `corrections.csv` | the downstream corrections (decision D18), applied in file order |
| `fusions-2021-2025.csv` | the reconduction of the 2021 municipality codes to the 2025 municipalities (decision D10) |
