# maps-slo

Partition of a set of territorial units into homogeneous local systems (SLO), each headed by a
centrality, from three inputs: a level per unit, a contiguity matrix and a travel-time matrix.
The rules are those of the MAPS project methodology (Gran Sasso Tech, GSSI); every parameter is
declared in a YAML scenario, and the engine assumes nothing about the identifiers, the number of
units or the number of levels.

SLO stands for *Sistemi Locali Omogenei* (homogeneous local systems). They are built on services,
contiguity and travel times, not on commuting flows: this is not an implementation of the ISTAT
labour market areas (*Sistemi Locali del Lavoro*, SLL). The project plan called the library
"maps-sll".

This is the **reference implementation, version 1.0**, of the algorithm specified and verified in
the MAPS deliverable D3.2.1. It is meant to be copied into the project's own repository and
maintained there: the code, the parameters and the inputs can be changed as the project needs.

## Quick start

```
uv venv --python 3.13 && uv pip install -e '.[dev,maps]'
.venv/bin/pytest                                                          # test suite
.venv/bin/maps-slo levels rules.yaml attributes.csv --out levels.parquet  # phase 1
.venv/bin/maps-slo run scenario.yaml --out output/                        # phases 2-4
```

## How the algorithm works

1. **Levels (phase 1)**: every unit gets a level from its services (health facilities, schools,
   stations) and population, or no level; units with a level are the *centralities*.
2. **Unions of centralities (phase 2)**: contiguous centralities within a time threshold and
   sharing enough border join, following a table of which levels may join which.
3. **Attraction (phase 3)**: every other unit joins the system of its nearest centrality.
4. **Single-unit systems (phase 4)**: systems left with one unit join a contiguous system.

Every step, rule code and parameter is described in the specification (D3.2.1, appendix A1),
linked under "Documents".

## Repository map

| Path | What it is |
|---|---|
| `src/maps_slo/` | **the library**, generic, with no Italian data. `engine.py` runs the phases in order; `levels.py` is phase 1; `phase2.py`, `phase3.py`, `phase4.py` are the aggregation; `scenario.py` reads and validates the YAML scenario; `problem.py` builds the problem from the inputs; `output.py`, `labels.py`, `metrics.py`, `manifest.py` write the tables, the system labels, the measures and the run manifest; `cli.py` is the `maps-slo` command |
| `tests/` | the test suite; test names carry the identifier of the D3.2.1 criterion they verify (for example `test_a12_...`) |
| `tools/` | `criteria.yaml` lists the D3.2.1 criteria; `traceability.py` turns the test report and the national checks into the criterion-by-criterion outcome table |
| `maps/` | **the application to the Italian municipalities (MAPS)**, outside the installable package; step-by-step commands in `maps/README.md` |
| `maps/prepare/` | input preparation: GSSI files, ISTAT population, reconduction of the 2021 travel-time matrix to the 2025 municipalities, phase-1 attributes from the GSSI services file |
| `maps/levels/` | the MAPS phase-1 rules (decision D16) |
| `maps/scenarios/` | the MAPS scenarios; `maps-2025-d16-cost-agreed.yaml` is the one of dataset version 1.0 |
| `maps/calibration/` | the calibration grids, run by `maps/calibrate.py` and read by `maps/choose.py` (and `maps/assignment.py` for an alternative cost) |
| `maps/reference/` | versioned reference tables: downstream corrections (decision D18), municipal fusions 2021-2025 (decision D10), texts of the D3.4 dataset package |
| `maps/corrections.py`, `checks.py`, `geo_export.py`, `package_d34.py` | after a run: downstream corrections, national checks, GeoJSON, D3.4 dataset package |
| `journal/` | dated design and plan documents, never updated after writing |
| `STATUS.md` | open work, one line per point |

## Calibration of version 1.0

The phase-2 parameters (time threshold, minimum shared border, table of the levels that may join)
were chosen with the method of the MAPS deliverable D3.3.2:

1. `maps/calibrate.py` runs the aggregation for the 1,638 combinations of the grid
   `maps/calibration/grid-2025-d16-cost.yaml` and computes the measures of the method for each;
2. a combination is admissible if at most 1% of the population is beyond 30 minutes from its
   centre, no non-distant municipality is beyond 60 minutes, and there are no more non-contiguous
   systems than with the parameters agreed with GSSI;
3. `maps/choose.py` minimises, among the admissible combinations, E = K1q - lambda * K5: K1q is
   the population-weighted mean of the squared extra minutes to the main centre (the cost of
   aggregating), K5 the population share in systems headed by a level 1-3 centre (the benefit),
   lambda the price of one point of benefit;
4. lambda is the smallest price for which the chosen combination reproduces the manual unions
   that the GSSI Stata routine applied by hand and that the algorithm can reach (4 of 7): the
   experts' corrections are read as revealed preferences.

Result: lambda between 11.25 and 11.6, time threshold 31 minutes with the agreed border share
(3.09%) and pairs table, 936 systems (934 after the downstream corrections). The minimum is
shallow between 26 and 31 minutes. Commands in `maps/README.md`, step 14.

## Data not included

The inputs of the national run are not in the repository (`maps/data/` is ignored). The
travel-time matrix (ISTAT, on TomTom graph) is not redistributed until its licence is cleared
with ISTAT; the redistributable inputs (levels, population, services) are published with the D3.4
dataset. Every run writes a manifest with the fingerprint of each input, so that a run can be
checked against a published one.

## Documents

- Specification of the algorithm (D3.2.1, appendix A1):
  https://docs.gst-maps.celata.com/wp3/A1-algorithm-specification.html
- Verification criteria and outcome (D3.2.1):
  https://docs.gst-maps.celata.com/wp3/01-slo-modules-verification.html
- Calibration method (D3.3.2, in Italian for now):
  https://docs.gst-maps.celata.com/it/wp3/02-slo-calibration.html

## Licence

Code: MIT (`LICENSE`). Data of the D3.4 dataset: see the licence file in the dataset package.
