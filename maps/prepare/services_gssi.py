"""Phase-1 attributes for every 2025 municipality from the GSSI services file.

    python maps/prepare/services_gssi.py maps/data/file_prova_algoritmo_modulo_1.xlsx \
        maps/data/services-2025.csv --health hospital_or_pnrr

The file (sheet "base", one row per municipality) gives presence flags for hospitals, DEA
and the community houses of PNRR Mission 6, the number of upper-secondary school types and
the highest RFI station category. Mapping to the attributes of maps/levels/maps-rules.yaml:

- population          <- Pop_1125
- n_dea               <- NUM_DEA (0/1)
- n_health            <- NUM_OSPEDALI, or NUM_OSPEDALI or PNRR_Missione6 with
                         --health hospital_or_pnrr (what counts as a health facility is a
                         question to GSSI: it decides about 400 centralities)
- n_secondary_schools <- "conta_tipi_scuole SUP": the number of school *types* (0-3), read as
                         the number of schools of decision D16 ("more than one")
- station_category    <- Stazioni_max_METALLI (Bronze..Platinum, decision D16); 0 = no station,
                         written empty (below the scale). The column Stazioni_max_nuova (the
                         newer RFI classification) is not used.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

STATIONS = {"bronze", "silver", "gold", "platinum"}
FLAGS = ["NUM_OSPEDALI", "NUM_DEA", "PNRR_Missione6"]


def services(path: Path, health: str) -> pd.DataFrame:
    d = pd.read_excel(path, sheet_name="base")
    need = ["Cod_COM", "Comune", "Pop_1125", *FLAGS, "conta_tipi_scuole SUP",
            "Stazioni_max_METALLI"]
    missing = [c for c in need if c not in d.columns]
    if missing:
        raise SystemExit(f"columns missing from the GSSI file: {missing}")
    ids = d["Cod_COM"].astype("int64").astype(str).str.zfill(6)
    if ids.duplicated().any():
        raise SystemExit(f"duplicated codes: {sorted(ids[ids.duplicated()])[:10]}")
    for c in [*FLAGS, "conta_tipi_scuole SUP", "Pop_1125"]:
        if d[c].isna().any() or (d[c] < 0).any():
            raise SystemExit(f"{c}: missing or negative values")
    for c in FLAGS:
        if not d[c].isin([0, 1]).all():
            raise SystemExit(f"{c}: expected presence flags 0/1")
    st = d["Stazioni_max_METALLI"].astype(str).str.strip().str.lower()
    bad = sorted(set(st) - STATIONS - {"0", "nan"})
    if bad:
        raise SystemExit(f"Stazioni_max_METALLI: unknown categories {bad}")
    if health == "hospital":
        n_health = d["NUM_OSPEDALI"]
    else:
        n_health = (d["NUM_OSPEDALI"] + d["PNRR_Missione6"]).clip(upper=1)
    return pd.DataFrame({
        "id": ids,
        "name": d["Comune"].astype(str),
        "population": d["Pop_1125"].astype("int64"),
        "n_health": n_health.astype("int64"),
        "n_dea": d["NUM_DEA"].astype("int64"),
        "n_secondary_schools": d["conta_tipi_scuole SUP"].astype("int64"),
        "station_category": st.where(st.isin(STATIONS), ""),
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--health", choices=["hospital", "hospital_or_pnrr"],
                    default="hospital_or_pnrr")
    a = ap.parse_args()
    df = services(a.xlsx, a.health)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} municipalities; health facility = {a.health}: {int(df.n_health.sum())}")


if __name__ == "__main__":
    main()
