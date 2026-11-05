# maps-slo

Partition of a set of territorial units into homogeneous local systems (SLO), each headed by a
centrality, from three inputs: a level per unit, a contiguity matrix and a travel-time matrix.
The rules are those of the MAPS project methodology (Gran Sasso Tech, GSSI); every parameter is
declared in a YAML scenario, and the engine assumes nothing about the identifiers, the number of
units or the number of levels.

SLO stands for *Sistemi Locali Omogenei*. They are built on services, contiguity and travel times,
not on commuting flows: this is not an implementation of the ISTAT labour market areas
(*Sistemi Locali del Lavoro*, SLL). The project plan called the library "maps-sll".

    maps-slo run scenario.yaml --out output/

## Italiano

`maps-slo` è la libreria dell'Algoritmo SLO del progetto MAPS (deliverable D3.5). La cartella
`maps/` contiene l'applicazione ai comuni italiani: conversione dei dati GSSI, riconduzione della
matrice dei tempi 2021 ai confini 2025, scenario MAPS. I dati non sono nel repository: la licenza
della matrice dei tempi ISTAT su grafo TomTom è in corso di verifica, e finché non è chiarita
l'esecuzione nazionale è riproducibile solo per chi ha accesso alla matrice.
