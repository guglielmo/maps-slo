# maps-sll

Partition of a set of territorial units into homogeneous local systems (SLO), each headed by a
centrality, from three inputs: a level per unit, a contiguity matrix and a travel-time matrix.
The rules are those of the MAPS project methodology (Gran Sasso Tech, GSSI); every parameter is
declared in a YAML scenario, and the engine assumes nothing about the identifiers, the number of
units or the number of levels.

    maps-sll run scenario.yaml --out output/

## Italiano

`maps-sll` è la libreria dell'Algoritmo SLO del progetto MAPS (deliverable D3.5). La cartella
`maps/` contiene l'applicazione ai comuni italiani: conversione dei dati GSSI, riconduzione della
matrice dei tempi 2021 ai confini 2025, scenario MAPS. I dati non sono nel repository: la licenza
della matrice dei tempi ISTAT su grafo TomTom è in corso di verifica, e finché non è chiarita
l'esecuzione nazionale è riproducibile solo per chi ha accesso alla matrice.
