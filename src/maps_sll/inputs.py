"""Inputs of the algorithm: units, contiguity, travel times (specification A1, "Perimetro")."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .scenario import Scenario

UNIT_COLUMNS = ["id", "name", "level", "weight"]
CONTIGUITY_COLUMNS = ["origin", "neighbour", "shared_length", "origin_perimeter"]
TIMES_COLUMNS = ["origin", "destination", "minutes"]


_NUMERIC_COLUMNS = ["level", "weight", "shared_length", "origin_perimeter", "minutes"]
_NA_TOKENS = ["", "NA", "N/A", "n/a", "NULL", "null", "NaN", "nan", "None", "<NA>", "#N/A"]


@dataclass
class Inputs:
    units: pd.DataFrame
    contiguity: pd.DataFrame
    times: pd.DataFrame
    times_description: str = "unspecified"
    _fingerprints: dict[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_paths(cls, units, contiguity, times, times_description: str) -> Inputs:
        paths = {"units": Path(units), "contiguity": Path(contiguity), "travel_times": Path(times)}
        inp = cls(
            units=_read(paths["units"], ["id"]),
            contiguity=_read(paths["contiguity"], ["origin", "neighbour"]),
            times=_read(paths["travel_times"], ["origin", "destination"], arrow=True),
            times_description=times_description,
        )
        inp._fingerprints = {k: "sha256:" + _file_sha256(p) for k, p in paths.items()}
        return inp

    @classmethod
    def from_scenario(cls, scenario: Scenario, base_dir: str | Path) -> Inputs:
        if scenario.inputs is None:
            raise ValueError("the scenario declares no inputs")
        base = Path(base_dir)
        ref = scenario.inputs
        return cls.from_paths(
            base / ref.units,
            base / ref.contiguity,
            base / ref.travel_times.path,
            ref.travel_times.description,
        )

    def fingerprints(self) -> dict[str, str]:
        """sha256 of the input files, or of the DataFrame content for in-memory inputs."""
        if not self._fingerprints:
            self._fingerprints = {
                "units": _frame_sha256(self.units),
                "contiguity": _frame_sha256(self.contiguity),
                "travel_times": _frame_sha256(self.times),
            }
        return self._fingerprints


def _read(path: Path, str_cols: list[str], arrow: bool = False) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(path, dtype_backend="pyarrow" if arrow else "numpy_nullable")
    elif suffix == ".csv":
        # Ids are opaque strings: "NA", "NULL", "" are valid ids, never missing values.
        # Only the known numeric columns get the usual NA tokens.
        df = pd.read_csv(
            path,
            dtype={c: str for c in str_cols},
            keep_default_na=False,
            na_values={c: _NA_TOKENS for c in _NUMERIC_COLUMNS},
        )
    else:
        raise ValueError(f"unsupported input format: {path}")
    return df


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _frame_sha256(df: pd.DataFrame) -> str:
    values = pd.util.hash_pandas_object(df, index=False).to_numpy()
    return "sha256:" + hashlib.sha256(values.tobytes()).hexdigest()
