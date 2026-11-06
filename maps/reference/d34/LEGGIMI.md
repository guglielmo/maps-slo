# Sistemi Locali Omogenei 2025 — dataset nazionale, versione {version}

Deliverable D3.4 del progetto MAPS (Multidimensional Area Place-based System, bando FRES 2, CUP B13C25001430001): dataset geospaziale nazionale dei Sistemi Locali Omogenei (SLO) e metadati associati.

## Che cos'è questa versione

È l'**esecuzione di riferimento** dell'algoritmo SLO sui comuni italiani del 2025, prodotta con la libreria «maps-slo» (deliverable D3.5), che implementa la specifica dell'algoritmo concordata con GSSI (appendice A1 del D3.2.1, decisioni D1-D26) ed è verificata contro i criteri del D3.2.1.

La versione {version} è completa: copre tutti i comuni italiani del 2025, con i metadati e i dati di ingresso necessari a rigenerarla. I parametri dell'aggregazione sono quelli che risultano dal metodo di calibrazione del D3.3.2; le definizioni dei servizi usate per i livelli seguono la decisione D16 sui dati forniti da GSSI il 5 novembre 2026. GST e GSSI, con i loro sviluppatori ed esperti, possono modificare e mantenere libreria, parametri e dati di ingresso secondo le proprie esigenze: il dataset si rigenera con i comandi del paragrafo «Come si rigenera», senza modifiche al codice quando cambiano solo parametri o dati, e ogni nuova esecuzione è una nuova versione.

## Contenuto

| File | Contenuto |
|---|---|
| `sistemi.gpkg`, `sistemi.geojson` | un poligono per sistema locale (unione dei confini comunali ISTAT 2025), con le misure come attributi |
| `comuni.gpkg`, `comuni.geojson` | un poligono per comune, con il sistema di appartenenza e il modo in cui vi è arrivato |
| `sistemi.csv`, `comuni.csv` | gli stessi attributi, senza geometria |
| `metadati/manifest.json` | versione del codice, parametri, impronta di ciascun dato di ingresso, macchina e software dell'esecuzione |
| `metadati/scenario.yaml` | i parametri dell'esecuzione |
| `metadati/metrics.json` | le misure dell'algoritmo (V2-V10 del D3.2.1), prima delle correzioni a valle |
| `metadati/corrections.json` | l'esito di ciascuna correzione a valle (decisione D18) |
| `metadati/campi.md` | la descrizione dei campi |
| `ingresso/` | i dati di ingresso ridistribuibili: comuni con popolazione e livello, attributi dei servizi, correzioni, fusioni comunali 2021-2025 |
| `SHA256SUMS` | l'impronta di ogni file del pacchetto |

Sistema di riferimento: WGS84 (EPSG:4326). Codici dei comuni: codice ISTAT a sei cifre (`PRO_COM_T`), confini al 1° gennaio 2025.

## Questa versione in numeri

- 7.896 comuni, tutti assegnati a un sistema;
- 934 sistemi dopo le correzioni a valle (936 in uscita dall'algoritmo), di cui 16 composti da un solo comune;
- 3 comuni distanti, oltre 60 minuti dal centro più vicino (Capraia Isola, Ponza, Ventotene);
- soglia di tempo per le unioni della fase 2: 31 minuti, con quota minima di confine condiviso del 3,09%.

## Punti che GST e GSSI possono rivedere

- **Calibrazione.** I parametri vengono dal metodo di calibrazione del D3.3.2, sottoposto alla validazione di GSSI. Il minimo della funzione di costo è poco profondo fra 26 e 31 minuti: una soglia diversa in quell'intervallo è difendibile.
- **Livelli.** Il calcolo dei livelli segue la decisione D16 sui dati dei servizi di GSSI. Restano da confermare con GSSI: le Case di comunità del PNRR come struttura sanitaria (con, 1.259 centralità; senza, 847), il numero di tipi di scuola letto come numero di scuole, la classificazione delle stazioni RFI, la data della popolazione.
- **Comuni senza tempi.** Misiliscemi (nato nel 2021, assente dalla matrice 2021) è assegnato a Trapani; le Isole Tremiti, senza collegamento stradale, sono un sistema di un solo comune. Entrambi sono correzioni a valle, elencate in `ingresso/correzioni.csv`.
- **Schema della tabella degli attrattori del WP2** (decisione D9): non ancora definito, quindi il dataset non è ancora nello schema del Datastore MAPS.

## Dati non inclusi

La **matrice dei tempi di percorrenza** (ISTAT, su grafo TomTom, comuni 2021 ricondotti al 2025 secondo la decisione D10) è necessaria per rigenerare il dataset ma non è inclusa: la sua licenza va verificata con ISTAT prima di qualsiasi ridistribuzione. Il manifesto ne riporta l'impronta, così chi la possiede può verificare di usare la stessa. Per la stessa ragione non sono inclusi i file della routine Stata di GSSI.

## Come si rigenera

Dal repository della libreria, con la matrice dei tempi in `maps/data/`:

```
maps-slo run maps/scenarios/maps-2025-d16-cost-agreed.yaml --out <dir>/run --manifest-extra maps/data/reconduction.json
python maps/corrections.py <dir>/run maps/reference/corrections.csv maps/data/units-2025-d16.parquet --out <dir>/corrected
python maps/geo_export.py <dir>/corrected <confini ISTAT 2025> --times maps/data/times-2025.parquet --units-input maps/data/units-2025-d16.parquet
python maps/package_d34.py <dir>/corrected <dir>/corrected/geo --version <versione> --units-input maps/data/units-2025-d16.parquet --services maps/data/services-2025.csv --out <pacchetto>
```

Per cambiare la calibrazione basta modificare `contiguity` e `distant_minutes` nello scenario; per cambiare le definizioni dei livelli, `maps/levels/maps-rules.yaml`. Le istruzioni complete sono in `maps/README.md` del repository.

## Fonti

- Confini comunali: ISTAT, «Limiti amministrativi» al 1° gennaio 2025, versione generalizzata.
- Popolazione residente: ISTAT, 1° gennaio 2025.
- Matrice dei tempi di percorrenza: ISTAT, su grafo TomTom (non inclusa).
- Attributi dei servizi (strutture sanitarie, DEA, Case di comunità PNRR, scuole secondarie superiori, stazioni RFI): file di GSSI del 5 novembre 2026.
- Algoritmo: specifica concordata fra consulente, GST e GSSI (D3.2.1, appendice A1), implementata nella libreria «maps-slo».
