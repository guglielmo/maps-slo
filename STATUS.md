# STATUS — where to resume

Outline of the open work, one line per point. Last update: 2026-11-05.

## maps-slo v0 — SLO algorithm library (MAPS deliverable D3.5), verified by the D3.2.1

Design: `journal/2026-11-04-design-maps-slo.md`. Plan: `journal/2026-11-05-piano-maps-slo.md` (14 tasks, all done).

Done:
- engine (phases 2–4), levels algorithm (phase 1), MAPS preparation, national run, traceability table; 156 tests
- first national run (2026-11-05): 7,896 municipalities, 991 systems, 3 distant (Capraia Isola, Ponza, Ventotene), 2 without times (Isole Tremiti 071026, Misiliscemi 081025), about 21 s; every national check satisfied, two runs with identical tables

Open points:
- criteria not verifiable yet (`output/esito.md`): R3 (run on a second machine), O1 (schema of the MAPS table of the attractors, decision D9); R2 and P3 are satisfied by a dated code reading, not by a test
- downstream unions (decision D18, confirmed 2026-11-05): Rome with Fiumicino and the six other unions of the GSSI routine (Carrara→Massa, Palagiano→Castellaneta, Pozzallo→Modica, Fiumefreddo→Giarre, San Marcello Piteglio→Pistoia, Santa Croce Camerina→Ragusa) are applied after every run, whatever systems come out: versioned list plus script on the algorithm output, keyed on the municipalities and not on the system ids, so that it applies to any calibration
- phase 1 follows decision D16, not the GSSI Stata routine (which predates the specification): the differences on levels 4–6 (574/1,259 matching, levels 1–3 all matching) are expected. The national aggregation still uses the GSSI levels as input, so its levels 4–6 are not those of D16 until the services data are available
- services data for all 2025 municipalities, needed by the levels algorithm (`centralità.dta` covers only the 1,259 centralities): source to agree with GSSI
- determinism rule of design section 6.6 (single-unit system both choosing and claimed): to confirm with GSSI
- output files of the GSSI Stata run, for the reconciliation: not received yet
- calibration of the aggregation parameters (share and time thresholds of phase 2, table of the level pairs that can merge; the distance threshold only flags units and does not change the assignment): parameters, ranges and objective measure to agree with GSSI
- Baranzate (015250) is missing from the 2025 population source and is added by hand to the population file

Links:
- **D3.2.1**: the traceability table of this repository (`tools/traceability.py`) becomes the "Esito" section of the verification document.
