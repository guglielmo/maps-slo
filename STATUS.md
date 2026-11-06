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
- Isole Tremiti (no road link, no travel times) stays a single-municipality system: correction C09 of kind `alone` (decision 2026-11-05)
- phase 1 follows decision D16, not the GSSI Stata routine (which predates the specification): the differences on levels 4–6 (574/1,259 matching, levels 1–3 all matching) are expected. The national aggregation still uses the GSSI levels as input, so its levels 4–6 are not those of D16 until the services data are available
- services data for all 2025 municipalities: GSSI file received 2026-11-05 (`file_prova_algoritmo_modulo_1.xlsx`, converted by `maps/prepare/services_gssi.py`). Open questions to GSSI: PNRR community houses as health facility (1,259 centralities with them, 847 without), school types read as number of schools, 0/1 flags, metal vs new RFI station classification, population date (`Pop_1125`). National run with D16 levels (hospital or PNRR): 988 systems, 29 municipalities change system against the GSSI-levels run
- determinism rule of design section 6.6 (single-unit system both choosing and claimed: its own choice prevails, the claimant stays alone): adopted 2026-11-05 and written into the specification (A1, "Trattamento simultaneo"); to communicate to GSSI, who may prefer a second round as in decision D26 (three national cases: Castel Volturno, Conversano, Castellaneta)
- output files of the GSSI Stata run, for the reconciliation: not received yet
- calibration (D3.3.2 draft, gst-maps `deliverables/docs/it/wp3/02-slo-calibration.md`, 2026-11-06): cost function E = K1q − λ·K5 (K1q = pop-weighted mean squared extra minutes) with constraints K3 ≤ 1%, K4 ≤ 60 min, V5 ≤ agreed (69); λ* = smallest price whose minimiser produces the 4 reachable GSSI unions (3 of 7 unreachable by D5/D14 and A6). Grid `maps/calibration/grid-2025-d16-cost.yaml` (1,638 combos) → `maps/choose.py`: λ* ≈ 11.25–11.6 → 31 minutes (agreed border/table: 936 systems, scenario `maps-2025-d16-cost-agreed`; all free: 0% border, pairs 4→3, 922, `maps-2025-d16-cost-free`); shallow minimum between 26 and 31 minutes; the 31 depends on one union (San Marcello Piteglio–Pistoia)
- open for GSSI: health facility (with community houses 1,259 centralities, hospitals only 847), weight of the GSSI unions in λ, border 0% vs D15 3.09%, the 3 unreachable unions
- note for Davide (interactive HTML page): being rebuilt on the cost function; still to write: the lambda-slider chart, then send it to Davide
- Baranzate (015250) is missing from the 2025 population source and is added by hand to the population file

Links:
- **D3.2.1**: the traceability table of this repository (`tools/traceability.py`) becomes the "Esito" section of the verification document.
