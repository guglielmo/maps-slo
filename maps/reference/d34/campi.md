# Descrizione dei campi

## `sistemi` (sistemi.gpkg, sistemi.geojson, sistemi.csv)

| Campo | Descrizione |
|---|---|
| `system_id` | codice ISTAT del comune centro del sistema; identifica il sistema |
| `name` | nome del comune centro |
| `main_centre_id` | codice del centro principale (coincide con `system_id`) |
| `main_centre_level` | livello del centro principale, da 1 (il più alto) a 6; vuoto per le Isole Tremiti, sistema creato da una correzione a valle |
| `n_units` | numero di comuni del sistema |
| `total_weight` | popolazione residente del sistema al 1° gennaio 2025 |
| `merged_centres_phase2` | centralità unite al sistema nella fase 2 (unioni per contiguità) |
| `merged_centres_phase4` | sistemi rimasti soli uniti nella fase 4 |
| `merged_centres_corrections` | sistemi uniti dalle correzioni a valle (decisione D18) |
| `max_chain_length` | numero massimo di passaggi di unione fra centralità dentro il sistema |
| `max_minutes_to_centre` | tempo massimo, in minuti, da un comune del sistema al centro principale |
| `mean_minutes_to_centre` | tempo medio al centro principale, ponderato con la popolazione |
| `color` | intero da 0 a 6 tale che due sistemi confinanti non hanno lo stesso valore, per la cartografia |

## `comuni` (comuni.gpkg, comuni.geojson, comuni.csv)

| Campo | Descrizione |
|---|---|
| `id` | codice ISTAT del comune (`PRO_COM_T`) |
| `name` | nome del comune |
| `cod_reg`, `cod_uts` | codice della regione e dell'unità territoriale sovracomunale |
| `system_id`, `system_name` | sistema di appartenenza: codice e nome del centro |
| `full_label` | nome del sistema; per una centralità unita, «centro(centralità)» |
| `role` | `main_centre` (centro del sistema), `merged_centre` (centralità unita a un altro sistema), `attracted` (comune non centralità) |
| `level` | livello della centralità da 1 a 6; vuoto per i comuni che non sono centralità |
| `direct_step_id`, `direct_step_name` | il comune verso cui questo comune si muove direttamente: la centralità più vicina (fase 3) o il centro a cui la centralità si unisce (fasi 2 e 4) |
| `minutes` | tempo, in minuti, verso `direct_step_id` |
| `chain` | la catena di passaggi fino al centro del sistema |
| `minutes_to_centre` | tempo diretto, in minuti, verso il centro del sistema; vuoto per Misiliscemi, senza tempi nella matrice |
| `distant` | `true` se il comune è oltre la soglia di lontananza (60 minuti) dal centro più vicino |
| `phase` | fase dell'algoritmo che ha deciso l'appartenenza (2, 3 o 4); vuoto per i comuni assegnati da una correzione a valle |
| `rule` | regola applicata, con il codice della specifica (appendice A1 del D3.2.1): `HEAD` centro, `P2-MERGE` unione della fase 2, `P3-NEAREST` attrazione verso la centralità più vicina, `P4-*` casi della fase 4 |
| `missing` | dati mancanti da cui l'esito dipende (vuoto in questa versione) |
| `unassigned` | `true` se il comune non è assegnato a nessun sistema (nessuno in questa versione) |
| `color` | il valore di `color` del sistema di appartenenza |

## `ingresso/`

| File | Contenuto |
|---|---|
| `comuni-livelli-popolazione.csv` | per comune: `id`, `name`, `level` (vuoto se non centralità), `weight` (popolazione al 1° gennaio 2025); è l'ingresso dell'algoritmo di aggregazione |
| `servizi-2025.csv` | per comune: popolazione e attributi dei servizi da cui il calcolo dei livelli (decisione D16) ricava il livello: `n_health` (strutture sanitarie, ospedali o Case di comunità PNRR), `n_dea`, `n_secondary_schools` (tipi di scuola secondaria superiore), `station_category` (categoria RFI della stazione principale) |
| `correzioni.csv` | le correzioni a valle (decisione D18), applicate nell'ordine del file |
| `fusioni-2021-2025.csv` | la riconduzione dei codici comunali 2021 ai comuni 2025 (decisione D10) |
