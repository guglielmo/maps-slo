# Design — maps-sll, the SLO algorithm library

Date of the decision: 4 November 2026. Agreed by Depp (consultant on the MAPS
project) after the MAPS meeting of the same day, in which GSSI confirmed that the code
of the algorithm is the Stata routine of 16 October 2026, and that no rewritten version
will follow.

## 1. Why this repository exists

The MAPS project (Multidimensional Area Place-based System, led by Gran Sasso Tech)
partitions Italy into *Sistemi Locali Omogenei* (SLO, homogeneous local systems): every
municipality is assigned to exactly one system headed by a *centrality*, a municipality
that offers a given level of services.

Three contract items meet in this repository:

| Item | What it is | Who |
|---|---|---|
| task 3.2 | the code of the SLO modules, with unit tests | development |
| D3.2.1 | technical verification and validation of the SLO modules | consultant |
| D3.5 | public repository of the "maps-sll" library, MIT licence, due 31/12/2026 | consultant |

The only code GSSI produced is the Stata routine of 16/10 (not redistributed here),
which predates
the decisions taken from the 7 October call onwards (D13–D26). The consultant therefore
implements the algorithm from the specification, in this repository, which becomes the
D3.5 library.

**Independence of the verification.** The same person writes the code and verifies it.
Two external checks compensate, and the D3.2.1 must say so explicitly: the reconciliation
report against the Stata routine of GSSI (section 9), and a review of the hand-built test
cases by GSSI.

## 2. Normative references

The code implements, and is verified against, two documents of the MAPS project:

- the **specification**: appendix A1 of the D3.2.1, version of 15 October 2026,
  which includes decisions D1–D26;
- the **acceptance criteria**: main document of the D3.2.1, criteria R1–R6, C1–C6,
  I1–I7, A1–A12, S1–S8, O1–O6, P1–P3 and metrics V2–V5, V9, V10.

Where this document and the specification disagree, the specification wins and this
document is wrong. Rules that the specification leaves open and that only serve
determinism are fixed here (section 6.6) and must be communicated to GSSI.

## 3. Scope

One repository, three parts with separate boundaries:

1. **the engine** (`src/maps_sll/`): phases 2, 3 and 4, scenario, label resolution,
   outputs, manifest, structural metrics. Generic: no ISTAT code, no fixed number of
   levels, no fixed number of units (criteria I1–I7);
2. **the level calculation** (`src/maps_sll/levels.py`): phase 1, a rule engine whose
   rules are configuration data (criteria C1–C6). It reads a table of attributes per unit
   and knows nothing about where the table comes from;
3. **the MAPS application** (`maps/`, outside the installable package): conversion of the
   GSSI `.dta` files, reconduction of the 2021 travel-time matrix to the 2025 municipal
   boundaries (decision D10, criterion R6), the MAPS scenario and level rules, the
   reconciliation with the Stata routine.

Out of scope, as the specification says: geometries (decision D19, they belong to the
national dataset D3.4); manual corrections such as Misiliscemi → Trapani (decision D18,
they belong to D3.4); comparison metrics V1, V6–V8 (they need external data).

## 4. Choice of approach

Three approaches were considered:

1. **Python and numpy, labels as pointers** — chosen. Units are indexed by position; the
   travel-time matrix is a dense float32 array (7,900 × 7,900 ≈ 250 MB); phase 3 is a
   vectorised `lexsort`; phases 2 and 4 each produce a *direct step* (one pointer per
   unit), and a single function resolves the chains with cycle protection. The code maps
   one-to-one onto the paragraphs of the specification, which is what makes it verifiable
   rule by rule.
2. **Everything in DuckDB/SQL** — rejected: recursive resolution and the simultaneous
   treatment of phase 4 become unreadable queries, and the link between criterion and code
   is lost.
3. **Polars or pandas tables** — rejected: no gain over (1), phases 2 and 4 remain graph
   logic.

DuckDB and pyarrow are used at the edges only (conversion of the `.dta` files, reading
Parquet).

## 5. Repository layout

```
maps-sll/
  pyproject.toml            # uv; Python 3.13; numpy, pandas, pyarrow, pyyaml, pydantic
  src/maps_sll/
    scenario.py             # YAML scenario → validated model (pydantic)
    inputs.py               # Units, Contiguity, TravelTimes; sha256 fingerprints
    levels.py               # phase 1: ordered rules, first match wins
    phase2.py               # merges between contiguous centralities
    phase3.py               # assignment of non-centralities
    phase4.py               # single-unit systems
    labels.py               # pointer resolution, chains, full labels, cycle errors
    engine.py               # run(scenario, inputs) -> Result; timings per phase
    output.py               # units table, systems table, distant units, manifest
    metrics.py              # V2–V5, V9, V10
    cli.py                  # maps-sll levels|run|metrics
  maps/                     # MAPS application, not packaged
    prepare/                # .dta → Parquet; 2021 → 2025 reconduction; population
    scenarios/maps-2025.yaml
    levels/maps-rules.yaml
    stata/                  # reconciliation report with the GSSI routine
    data/                   # gitignored: GSSI .dta files, Parquet conversions
  tests/
    cases/*.yaml            # hand-built cases, one file per criterion
    test_<criterion>.py     # test names carry the criterion id
  tools/traceability.py     # junit xml → criteria/tests/outcome table for the D3.2.1
  journal/  STATUS.md  README.md (English, with an Italian section)  LICENSE (MIT)
```

## 6. The engine

### 6.1 Inputs

| Input | Content | Notes |
|---|---|---|
| units | `id` (opaque string), `name`, `level` (int or null), `weight` (float) | `weight` is the resident population in MAPS; needed for **all** units, not only centralities (system weights, metric V4) |
| contiguity | `origin`, `neighbour`, `shared_length`, `origin_perimeter` | directed rows; the share is `shared_length / origin_perimeter`, computed on the unit that joins (specification, paragraph "Contiguità rilevante") |
| travel times | `origin`, `destination`, `minutes` | loaded into a dense matrix; missing pairs are NaN; the direction used is always *from the unit that joins or is assigned* to the centrality |
| scenario | YAML file, section 6.2 | the only source of parameters (criterion R2) |

Identifiers are never parsed. Their order for tie-breaks comes from the scenario
(`id_order: lexicographic | numeric | explicit`), which protects criterion I6.

### 6.2 Scenario

```yaml
name: maps-2025
reference_year: 2025
levels: [1, 2, 3, 4, 5, 6]          # ordered from strongest to weakest
phase2_pairs:                        # merged level -> allowed main-centre levels
  2: [1]
  3: [1]
  4: [1, 2]
  5: [1, 2, 3]
  6: [1, 2, 3]
phase4_levels: [4, 5, 6]
contiguity:
  min_shared_share: 0.0309           # strictly greater than (decision D15)
  max_minutes: 20                    # strictly less than (decision D15)
distant_minutes: 60                  # strictly greater than → flagged (decisions D1, D2)
id_order: numeric
max_chain_length: 16                 # resolution guard (criterion A9)
inputs:
  units: data/units-2025.parquet
  contiguity: data/contiguity-2025.parquet
  travel_times: {path: data/times-2021-to-2025.parquet, description: "ISTAT, TomTom graph, free-flow, 2021 reconducted to 2025"}
```

Validation at load time: every declared phase-2 pair must point to a strictly stronger
level (the invariant of the specification, paragraph "Quali centralità si uniscono"),
otherwise the scenario is rejected with an error naming the pair. The table above is the
MAPS one, rules 1–3 of decisions D5 and D14, written per merged level.

### 6.3 Phase 2 — merges between contiguous centralities

For every centrality `c`, the candidates are the centralities `t` such that:
the contiguity is relevant (share on the perimeter of `c` greater than the threshold,
time from `c` to `t` lower than the threshold) and `level(t)` is in
`phase2_pairs[level(c)]`. Among the candidates, `c` points to the one with the strongest
level, then the greatest weight, then the smallest identifier rank.

One pass is enough to reach the fixpoint the specification asks for ("le unioni si
applicano finché nessuna centralità può unirsi ulteriormente"): the candidate set of a
centrality depends only on attributes that phase 2 never changes (level, contiguity,
times), so a second pass would produce the same pointers. Chains such as 5 → 3 → 1 come
from the resolution, not from iterations. `max_chain_length` guards the resolution.

### 6.4 Phase 3 — assignment

Every non-centrality `u` with at least one finite time to a centrality points to the
centrality minimising, in order: time from `u`; level strength; weight (descending);
identifier rank (decisions D21, D22). All centralities compete, merged ones included,
each with its **own** level and weight. `u` is flagged *distant* when that time is
greater than `distant_minutes`. Non-centralities with no finite time go to the list of
units without times (criterion R6), not to an error.

Implementation: one `numpy.lexsort` per row block over the centrality columns of the
matrix; about 6,630 × 1,259 ≈ 8.3 million comparisons with the GSSI levels.

### 6.5 Phase 4 — single-unit systems

State: the pointers at the end of phase 3, frozen. A *single-unit system* is a centrality
that heads its own system (no outgoing pointer) and to which no unit and no centrality
points.

For each single-unit system `s` with `level(s)` in `phase4_levels`, the candidates are
the centralities contiguous to `s` in the relevant sense (same thresholds, share on the
perimeter of `s`), of any level, ordered by time from `s`, then weight descending, then
identifier rank (decision D24). The candidates are visited in order:

| Candidate `c` | Outcome | Rule id |
|---|---|---|
| `c` is a single-unit system with a level not in `phase4_levels` | `s → c`, always (decision D25) | `P4-D25` |
| weight of `c` greater than weight of `s` | `s → c`, `s` joins as a merged centre | `P4-JOIN` |
| weight of `c` lower, and `c` is merged into another centrality | skip, try the next candidate (decisions D23, D26) | `P4-SKIP` |
| weight of `c` lower, and `c` heads its own system | `c` is *claimed* by `s` | `P4-CLAIM` |
| no candidate left | `s` stays alone, a legitimate outcome | `P4-ALONE` |

Equal weights are broken by identifier rank, the smaller rank counting as heavier.
Claims are resolved after all single-unit systems have chosen: a claimed centrality
points to the heaviest claimant (specification, paragraph "Trattamento simultaneo").

Phase 4 never changes a phase-3 pointer of a non-centrality (criterion A11): it only
adds pointers between centralities.

### 6.6 Determinism rules fixed here

The specification leaves one case open, and this document fixes it as a determinism rule,
to be communicated to GSSI:

- **a single-unit system that has its own outcome and is also claimed.** A single-unit
  system `c` can both choose a heavier centrality (`c → d`) and be claimed by a heavier
  single-unit system `s`. Its own choice prevails, and the claim has no effect. The
  reason: each single-unit system decides first for itself; a claim is a decision taken
  about someone else.

Every pointer produced in phase 4 goes from a lighter to a heavier centrality, in the
total order (weight, identifier rank), or towards a centrality that has no outgoing
pointer (`P4-D25`): no cycle can form. The resolution keeps its guard anyway.

### 6.7 Label resolution

`labels.py` takes the pointers of all phases and returns, for every unit: the *system*
(the root, a centrality with no outgoing pointer), the chain (`X → Sesto San Giovanni →
Milano`), the full label (`Milano` for the main centre and for the units it attracts
directly; `Milano(X)` for a merged centre X and for the units that enter the system
through X, where X is the merged centre itself or the direct step; never nested), the role (`main_centre`, `merged_centre`,
`attracted`) and the phase that produced the membership. A chain longer than
`max_chain_length`, or a revisited unit, raises `ChainError` with the unit identifiers
(criterion A9).

## 7. The level calculation (phase 1)

Rules are evaluated in order, the first one that applies wins (decision D7). Each rule
has an id, a level and a condition built from three predicate forms (no `eval`):

```yaml
rules:
  - {id: L1, level: 1, all: [{attr: population, op: ">=", value: 250000}]}
  - {id: L4, level: 4, all: [{attr: n_dea, op: ">=", value: 1},
                             {attr: n_secondary_schools, op: ">", value: 1},
                             {attr: station_category, op: ">=", value: silver}]}
  - {id: L6, level: 6, exactly: 2, of: [{name: health,  attr: n_health,  op: ">=", value: 1},
                                        {name: school,  attr: n_secondary_schools, op: ">=", value: 1},
                                        {name: station, attr: station_category, op: ">=", value: bronze}]}
ordinal_attributes:
  station_category: [bronze, silver, gold, platinum]
```

Output: `id`, `level` (or null), `rule_id` (criterion C3), `missing` (for `exactly`
rules, the names of the false predicates: the missing service of level 6, criterion C6).

**Data.** The national input of phase 1 is not available yet. The GSSI file
`centralità.dta` contains only the 1,259 centralities (levels 1–6: 11, 33, 93, 141, 286,
695). The MAPS Datastore has population, upper-secondary schools and the level of
emergency departments (DEA, in the raw AGENAS file only), but not the RFI station category
nor the full list of health facilities. Until the attributes for all municipalities are
available (requested from GSSI on 4 November), the national run uses the GSSI levels
as input, and phase 1 is verified on hand-built cases (C1–C6) and reconciled on the
1,259 rows available.

## 8. Outputs

Written to an output directory, Parquet plus CSV for the tables:

- `units` — one row per unit present in the travel-time matrix: the fields of the
  specification, paragraph "Tavola dei comuni" (id, name, level, missing service, direct
  step, system, full label, chain, role, minutes to the direct step, distant flag, phase,
  rule id);
- `systems` — id, name, main centre, merged centres from phase 2 and from phase 4, total
  weight, number of units;
- `distant` — the distant units with their system (criterion S7);
- `unassigned` — units without times (criterion R6);
- `manifest.json` — scenario (full copy), package version and git commit, sha256 of every
  input, reference year, thresholds actually used, travel-time matrix description,
  reconduction lists, number of systems whose centre changes in phase 4, timings per phase
  (criterion P2), start and end time;
- `metrics.json` — V2, V3, V4, V5, V9, V10.

## 9. Reconciliation with the GSSI Stata routine

The Stata routine is a comparison term for phases 1–3, not an oracle. The report in
`maps/stata/` lists every difference between its output and ours, each with the decision
that explains it. The differences already expected:

| Point | Stata routine of 16/10 | Specification | Decision |
|---|---|---|---|
| units beyond a time limit | pairs over 90 minutes dropped before assignment (line 390) | every unit assigned, those over 60 minutes flagged | D1, D2 |
| shared-border threshold | 10th percentile recomputed on the data (3.079%) | fixed 3.09% | D15 |
| level of the merged centrality in the tie-break | not regulated | own level and weight | D22 |
| phase 4 | previous version | population criterion, Abano cases | D13, D23–D26 |
| level-3 centralities contiguous to level 1 | manual step (line 318) | automatic, through the declared pairs | D14 |
| definition of levels 4 and 5 | PNRR Mission 6 interventions count as health facilities; SNAI index of school variety | DEA, more than one school, station ≥ Silver; any health facility | D16, question to GSSI pending |

Since Stata is not available locally, the comparison needs the output files of the GSSI
run (the `DLS2` file and the final result), requested from GSSI.

## 10. MAPS data preparation (`maps/prepare/`)

1. **Conversion**: the four `.dta` files of the GSSI zip become Parquet. The travel-time
   matrix (`distanze_2021.dta`, 2.4 GB) is read in chunks and keeps `cod_istat_or`,
   `cod_istat_dest`, `ttp_tot` (free-flow minutes, decision D17); `tep_tot` and `km_tot`
   (decimal comma) are dropped.
2. **Reconduction 2021 → 2025** (decision D10): for every merger, the row and column of
   the municipality that hosts the town hall of the new municipality survive under the 2025
   code; the others are dropped. Output: the list of reconducted units with the unit that
   took their place, and the list of 2025 units without times (Misiliscemi). The
   correspondence table comes from the ISTAT list of administrative changes 2021–2025,
   committed as an open-data CSV.
3. **Population 2025 for all municipalities** from the Datastore (ISTAT), because the
   GSSI file has it only for centralities.
4. **Units table** = population + GSSI levels (later: output of phase 1 on the
   Datastore attributes).

The contiguity file covers 7,889 municipalities; island municipalities without neighbours
are absent and are handled as units with no contiguity rows.

## 11. Verification and traceability

- Each hand-built case is a YAML file in `tests/cases/` (units, contiguity, times, scenario
  overrides, expected pointers and systems). Test functions carry the criterion id:
  `test_A6_undeclared_pair_3_to_2`, `test_A12_case7_abano_heavier_than_y`.
- Property tests: R1 (two runs, identical files), R4 (shuffled inputs, identical outputs
  of every phase), I6 (200 synthetic units with non-ISTAT ids), A9 (circular chain →
  `ChainError`).
- National-run checks (R3, R6, C1, S1, S5, O2, O3, P1–P3) live in
  `maps/checks.py` and run on the real data, outside CI.
- `tools/traceability.py` turns the pytest junit report into the table criterion → tests →
  outcome (satisfied, not satisfied, not verifiable), which becomes the "Esito" section of
  the D3.2.1.
- CI on GitHub Actions runs the unit tests only (no data in the repository).

Criteria that cannot be satisfied by this repository alone are declared, not hidden:
O1 depends on decision D9 (schema of the MAPS table of the attractors, WP2), I2 and I5 partly too.

## 12. Performance

Expected: reading the matrix dominates (62 million pairs from Parquet, seconds);
phase 3 is about 8.3 million comparisons, phases 2 and 4 work on a few thousand pairs.
The P1 limit (ten minutes, decision D20) leaves a wide margin. P3 is met by keeping the
reconducted matrix as a Parquet file reused by every scenario.

## 13. Publication

Local development first, then `github.com/GranSassoTech/maps-sll`, MIT licence, after
the consultant's review. No data in the repository (`maps/data/` is gitignored): the
licence of the ISTAT travel-time matrix built on the TomTom graph is still to be checked
with ISTAT (open point of the specification), and until then the README says that the
national run is reproducible only for whoever has access to the matrix.

## 14. Order of work

1. scaffold, scenario and inputs;
2. label resolution;
3. phase 2, phase 3, phase 4, each with its hand-built cases;
4. outputs, manifest, metrics;
5. phase 1 rule engine;
6. MAPS preparation: conversion, reconduction, population;
7. national run with GSSI levels, checks, P1 timing;
8. Stata reconciliation (needs the GSSI output files);
9. traceability table and D3.2.1 "Esito" section;
10. publication on GitHub.

## 15. Open points

- attributes of the services for all municipalities and source of the RFI category and of
  the health facilities: asked to GSSI on 4 November;
- definitions of levels 4 and 5 (PNRR Mission 6, SNAI index) versus decision D16: asked
  to GSSI;
- output files of the Stata run, for the reconciliation: asked to GSSI;
- the determinism rule of section 6.6: to be communicated to GSSI;
- decision D9 (schema of the MAPS table of the attractors): with development, conditions O1;
- licence of the travel-time matrix: with ISTAT.
