# STATUS — where to resume

Outline of the open work, one line per point. Last update: 2026-11-05.

## maps-sll v0 — SLO algorithm library (MAPS deliverable D3.5), verified by the D3.2.1

Design: `journal/2026-11-04-design-maps-sll.md`. Plan: `journal/2026-11-05-piano-maps-sll.md` (14 tasks, all done).

Done:
- engine (phases 2–4), levels algorithm (phase 1), MAPS preparation, national run, traceability table; 156 tests
- first national run (2026-11-05): 7,896 municipalities, 991 systems, 3 distant (Capraia Isola, Ponza, Ventotene), 2 without times (Isole Tremiti 071026, Misiliscemi 081025), about 21 s; every national check satisfied, two runs with identical tables

Open points:
- criteria not verifiable yet (`output/esito.md`): R3 (run on a second machine), O1 (schema of the MAPS table of the attractors, decision D9); R2 and P3 are satisfied by a dated code reading, not by a test
- Rome forms a one-municipality system: every neighbour is more than 20 minutes from the centroid of Rome, so no phase-2 merge applies; the GSSI Stata run gives the same result and fixes it by hand (Fiumicino joins Rome), which decision D18 leaves to the downstream corrections: to discuss with GSSI
- phase 1 against the GSSI levels (`maps/levels_gssi.py`): levels 1–3 coincide (137/137), 574/1,259 overall; the GSSI routine counts as health service a hospital or a PNRR Mission 6 facility, and for level 4 requires hospital and schools without DEA and station: both differ from decision D16, to settle with GSSI
- services data for all 2025 municipalities, needed by the levels algorithm (`centralità.dta` covers only the 1,259 centralities): source to agree with GSSI
- determinism rule of design section 6.6 (single-unit system both choosing and claimed): to confirm with GSSI
- output files of the GSSI Stata run, for the reconciliation: not received yet
- calibration of the aggregation parameters (share and time thresholds of phase 2, distance threshold): parameters, ranges and objective measure to agree with GSSI
- Baranzate (015250) is missing from the 2025 population source and is added by hand to the population file

Links:
- **D3.2.1**: the traceability table of this repository (`tools/traceability.py`) becomes the "Esito" section of the verification document.
