# maps-sll — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** build the `maps-sll` library as two separate algorithms, each run and calibrated on its own — the level calculation (phase 1, `maps-sll levels`) and the aggregation (phases 2–4, `maps-sll run`) — and the MAPS application that runs it on the Italian municipalities, with every acceptance criterion of the D3.2.1 traceable to a test or a national check.

**Architecture:** generic engine in `src/maps_sll/` working on opaque unit identifiers; numpy dense travel-time matrix; phases 2 and 4 produce one pointer per unit, a single resolver follows the chains with cycle protection; all parameters come from a YAML scenario. The Italian part (conversion of the GSSI files, reconduction of the 2021 matrix, MAPS scenario) lives in `maps/`, outside the package.

**Tech Stack:** Python 3.13, uv, numpy, pandas, pyarrow, pydantic v2, PyYAML, pytest, ruff; DuckDB only in `maps/` for the data preparation.

**Design:** `journal/2026-11-04-design-maps-sll.md`. Normative references: appendix A1 (specification) and main document (criteria) of the MAPS deliverable D3.2.1.

**Decision of 2026-11-05.** The two algorithms are never chained in one command: levels are a product of their own, with their own manifest, so each can be calibrated without re-running the other. The national aggregation starts from the GSSI levels (`centralità.dta`) until the services data for all municipalities are agreed with GSSI.

**Not in this plan** (separate plans, blocked on external inputs): reconciliation with the GSSI Stata routine (needs the GSSI output files), phase-1 national input from the Datastore (needs the RFI category and the health-facility source), publication on GitHub.

---

## File structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | package metadata, dependencies, pytest and ruff config |
| `src/maps_sll/__init__.py` | public API, `__version__` |
| `src/maps_sll/scenario.py` | `Scenario` model, invariant checks, `load_scenario()` |
| `src/maps_sll/inputs.py` | `Inputs` (three DataFrames + times description), file loading, fingerprints |
| `src/maps_sll/problem.py` | `Problem` (arrays indexed by unit position), `build_problem()`, `InputError` |
| `src/maps_sll/labels.py` | `resolve()` of pointer chains, `ChainError` |
| `src/maps_sll/phase2.py` | merges between contiguous centralities |
| `src/maps_sll/phase3.py` | assignment of non-centralities, `Phase3Result` |
| `src/maps_sll/phase4.py` | single-unit systems, `Phase4Result` |
| `src/maps_sll/engine.py` | `run()`, `Result`, rule and phase per unit, timings |
| `src/maps_sll/output.py` | units/systems/distant/unassigned tables, `write_outputs()` |
| `src/maps_sll/metrics.py` | V2–V5, V9, V10 |
| `src/maps_sll/manifest.py` | run manifest |
| `src/maps_sll/levels.py` | phase-1 rule engine |
| `src/maps_sll/cli.py` | `maps-sll run` and `maps-sll levels` |
| `tests/builders.py` | helpers to build hand-written cases |
| `tests/test_*.py` | one module per area, test names carry the criterion id |
| `maps/prepare/convert.py` | GSSI `.dta` → Parquet |
| `maps/prepare/fusions_draft.py` | draft of the 2021→2025 correspondence table |
| `maps/prepare/reconduct.py` | 2021 matrix → 2025 codes (decision D10), R6 lists |
| `maps/prepare/build_units.py` | units table = population 2025 + GSSI levels |
| `maps/levels/maps-rules.yaml` | MAPS phase-1 rules |
| `maps/levels_gssi.py` | our phase 1 vs GSSI levels on the 1,259 centralities |
| `maps/scenarios/maps-2025.yaml` | MAPS scenario |
| `maps/checks.py` | national-run checks (R6, C1, S1, S5, S8, O2, O3, P1, P2) |
| `tools/criteria.yaml`, `tools/traceability.py` | criterion → evidence → outcome table |

Hand-built cases are written as Python builders in the test modules, not as YAML files as the design suggested: same content, less code, and the expected outcome sits next to the case.

---

### Task 1: Scaffold

**Files:**
- Create: `pyproject.toml`, `src/maps_sll/__init__.py`, `tests/test_smoke.py`, `LICENSE`, `README.md`, `.github/workflows/tests.yml`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "maps-sll"
version = "0.1.0"
description = "Homogeneous local systems (SLO): partition of territorial units around centralities"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
dependencies = [
  "numpy>=2.0",
  "pandas>=2.2",
  "pyarrow>=16",
  "pyyaml>=6",
  "pydantic>=2.7",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.6"]
maps = ["duckdb>=1.1"]

[project.scripts]
maps-sll = "maps_sll.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/maps_sll"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Write `src/maps_sll/__init__.py`**

```python
"""maps-sll: homogeneous local systems (SLO) around centralities."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("maps-sll")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0+unknown"
```

- [ ] **Step 3: Write the smoke test `tests/test_smoke.py`**

```python
import maps_sll


def test_version_is_set():
    assert maps_sll.__version__
```

- [ ] **Step 4: Create the environment and run the test**

Run: `cd maps-sll && uv venv --python 3.13 && uv pip install -e '.[dev,maps]' && .venv/bin/pytest`
Expected: `1 passed`

- [ ] **Step 5: Write `LICENSE` (MIT, "Copyright (c) 2026 Gran Sasso Tech") and `README.md`**

`README.md`:

```markdown
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
```

- [ ] **Step 6: Write `.github/workflows/tests.yml`**

```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv venv --python 3.13 && uv pip install -e '.[dev]'
      - run: .venv/bin/ruff check src tests
      - run: .venv/bin/pytest --junitxml=junit.xml
      - uses: actions/upload-artifact@v4
        with: {name: junit, path: junit.xml}
```

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "chore: scaffold maps-sll package"
```

---

### Task 2: Scenario

**Files:**
- Create: `src/maps_sll/scenario.py`, `tests/builders.py` (scenario part), `tests/test_scenario.py`

- [ ] **Step 1: Write `tests/builders.py` (scenario part only; the rest comes in Task 3)**

```python
"""Helpers to write hand-built test cases."""

from __future__ import annotations

from maps_sll.scenario import Scenario

MAPS = {
    "name": "test-maps",
    "reference_year": 2025,
    "levels": [1, 2, 3, 4, 5, 6],
    "phase2_pairs": {2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3], 6: [1, 2, 3]},
    "phase4_levels": [4, 5, 6],
    "contiguity": {"min_shared_share": 0.0309, "max_minutes": 20},
    "distant_minutes": 60,
    "id_order": "lexicographic",
    "max_chain_length": 16,
}


def scenario(**overrides) -> Scenario:
    """MAPS parametrisation (decisions D5, D13, D14, D15), with overrides."""
    return Scenario.model_validate({**MAPS, **overrides})
```

- [ ] **Step 2: Write the failing tests `tests/test_scenario.py`**

```python
import pytest

from builders import MAPS, scenario
from maps_sll.scenario import load_scenario


def test_maps_scenario_is_valid():
    sc = scenario()
    assert sc.strength(1) == 0 and sc.strength(6) == 5


def test_A6_invariant_rejects_pair_toward_weaker_level():
    with pytest.raises(ValueError, match="invariant"):
        scenario(phase2_pairs={2: [3]})


def test_A6_invariant_rejects_pair_between_equal_levels():
    with pytest.raises(ValueError, match="invariant"):
        scenario(phase2_pairs={4: [4]})


def test_I2_levels_are_a_parameter():
    sc = scenario(levels=[1, 2, 3, 4, 5, 6, 7], phase2_pairs={**MAPS["phase2_pairs"], 7: [1, 2, 3]})
    assert sc.strength(7) == 6


def test_unknown_level_in_phase4_levels_rejected():
    with pytest.raises(ValueError, match="phase4_levels"):
        scenario(phase4_levels=[9])


def test_explicit_order_requires_list():
    with pytest.raises(ValueError, match="id_order_list"):
        scenario(id_order="explicit")


def test_load_scenario_from_yaml(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(
        "name: x\nreference_year: 2025\nlevels: [1, 2]\nphase2_pairs: {2: [1]}\n"
        "phase4_levels: [2]\ncontiguity: {min_shared_share: 0.03, max_minutes: 20}\n"
        "distant_minutes: 60\n",
        encoding="utf-8",
    )
    sc = load_scenario(p)
    assert sc.phase2_pairs == {2: [1]} and sc.id_order == "lexicographic"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_scenario.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'maps_sll.scenario'`

- [ ] **Step 4: Write `src/maps_sll/scenario.py`**

```python
"""Scenario: the only source of parameters of an execution (criterion R2)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator


class Contiguity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_shared_share: float  # relevant when the share is strictly greater
    max_minutes: float  # relevant when the time is strictly lower


class TravelTimesRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    description: str


class InputPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")
    units: str
    contiguity: str
    travel_times: TravelTimesRef


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    reference_year: int
    levels: list[int]  # from strongest to weakest
    phase2_pairs: dict[int, list[int]]  # merged level -> allowed main-centre levels
    phase4_levels: list[int]
    contiguity: Contiguity
    distant_minutes: float  # strictly greater -> flagged as distant
    id_order: Literal["lexicographic", "numeric", "explicit"] = "lexicographic"
    id_order_list: list[str] | None = None
    max_chain_length: int = 16
    inputs: InputPaths | None = None

    @model_validator(mode="after")
    def _check(self) -> "Scenario":
        if len(set(self.levels)) != len(self.levels):
            raise ValueError("levels must be unique")
        if any(lv < 0 for lv in self.levels):
            raise ValueError("levels must be non-negative integers")
        rank = {lv: i for i, lv in enumerate(self.levels)}
        for merged, mains in self.phase2_pairs.items():
            if merged not in rank:
                raise ValueError(f"phase2_pairs: level {merged} is not declared in levels")
            for main in mains:
                if main not in rank:
                    raise ValueError(f"phase2_pairs: level {main} is not declared in levels")
                if rank[main] >= rank[merged]:
                    raise ValueError(
                        f"phase2_pairs: pair {merged} -> {main} violates the invariant: "
                        "the main centre must be of a strictly stronger level"
                    )
        for lv in self.phase4_levels:
            if lv not in rank:
                raise ValueError(f"phase4_levels: level {lv} is not declared in levels")
        if self.id_order == "explicit" and not self.id_order_list:
            raise ValueError("id_order 'explicit' requires id_order_list")
        if self.max_chain_length < 1:
            raise ValueError("max_chain_length must be at least 1")
        return self

    def strength(self, level: int) -> int:
        """Position of the level in the scheme: 0 is the strongest."""
        return self.levels.index(level)


def load_scenario(path: str | Path) -> Scenario:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Scenario.model_validate(data)
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/pytest tests/test_scenario.py`
Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: scenario model with phase-2 invariant"
```

---

### Task 3: Inputs and problem

**Files:**
- Create: `src/maps_sll/inputs.py`, `src/maps_sll/problem.py`, `tests/test_problem.py`
- Modify: `tests/builders.py` (append)

- [ ] **Step 1: Replace `tests/builders.py` with the full version**

```python
"""Helpers to write hand-built test cases."""

from __future__ import annotations

import pandas as pd

# from maps_sll.engine import run  # uncomment in Task 7
from maps_sll.inputs import Inputs
from maps_sll.problem import Problem, build_problem
from maps_sll.scenario import Scenario

MAPS = {
    "name": "test-maps",
    "reference_year": 2025,
    "levels": [1, 2, 3, 4, 5, 6],
    "phase2_pairs": {2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3], 6: [1, 2, 3]},
    "phase4_levels": [4, 5, 6],
    "contiguity": {"min_shared_share": 0.0309, "max_minutes": 20},
    "distant_minutes": 60,
    "id_order": "lexicographic",
    "max_chain_length": 16,
}


def scenario(**overrides) -> Scenario:
    """MAPS parametrisation (decisions D5, D13, D14, D15), with overrides."""
    return Scenario.model_validate({**MAPS, **overrides})


def make_inputs(units, contig=(), times=None, description="test matrix") -> Inputs:
    """units: (id, level|None, weight[, name]); contig: (a, b[, share_ab[, share_ba]]);
    times: {(a, b): minutes}, mirrored to (b, a) unless given; diagonal is 0.
    Shares are written as shared_length with perimeter 1.0, so thresholds compare exactly."""
    u = pd.DataFrame(
        [
            {"id": x[0], "name": x[3] if len(x) > 3 else x[0], "level": x[1], "weight": float(x[2])}
            for x in units
        ]
    )
    u["level"] = u["level"].astype("Int64")
    rows = []
    for e in contig:
        a, b = e[0], e[1]
        sab = e[2] if len(e) > 2 else 0.5
        sba = e[3] if len(e) > 3 else sab
        rows.append({"origin": a, "neighbour": b, "shared_length": sab, "origin_perimeter": 1.0})
        rows.append({"origin": b, "neighbour": a, "shared_length": sba, "origin_perimeter": 1.0})
    c = pd.DataFrame(rows, columns=["origin", "neighbour", "shared_length", "origin_perimeter"])
    t = dict(times or {})
    for (a, b), m in list(t.items()):
        t.setdefault((b, a), m)
    for x in units:
        t[(x[0], x[0])] = 0.0
    tr = pd.DataFrame(
        [{"origin": a, "destination": b, "minutes": float(m)} for (a, b), m in t.items()],
        columns=["origin", "destination", "minutes"],
    )
    return Inputs(units=u, contiguity=c, times=tr, times_description=description)


def problem(units, contig=(), times=None, sc=None) -> Problem:
    return build_problem(make_inputs(units, contig, times), sc or scenario())


def ix(p: Problem, uid: str) -> int:
    return p.index[uid]


# Uncomment in Task 7, together with the engine import above.
# def run_case(units, contig=(), times=None, sc=None):
#     return run(sc or scenario(), make_inputs(units, contig, times))
#
#
# def step(r, uid: str):
#     j = r.ptr4[ix(r.problem, uid)]
#     return None if j == -1 else r.problem.ids[j]
#
#
# def system_of(r, uid: str) -> str:
#     return r.problem.ids[r.roots[ix(r.problem, uid)]]
```

- [ ] **Step 2: Write the failing tests `tests/test_problem.py`**

```python
import numpy as np
import pytest

from builders import make_inputs, problem, scenario
from maps_sll.problem import InputError, build_problem


def test_arrays_are_indexed_by_position():
    p = problem([("a", 1, 100), ("b", None, 10)], [("a", "b", 0.2, 0.4)], {("a", "b"): 7})
    a, b = p.index["a"], p.index["b"]
    assert p.is_centrality[a] and not p.is_centrality[b]
    assert p.level[b] == -1 and p.strength[a] == 0
    assert p.times[a, b] == 7 and p.times[b, a] == 7 and p.times[a, a] == 0
    assert p.neighbours[a] == [(b, 0.2)] and p.neighbours[b] == [(a, 0.4)]


def test_missing_times_are_nan():
    p = problem([("a", 1, 100), ("b", None, 10)])
    assert np.isnan(p.times[0, 1])


def test_I6_lexicographic_order():
    p = problem([("9", 1, 1), ("10", 1, 1)])
    assert p.id_rank[p.index["10"]] < p.id_rank[p.index["9"]]


def test_I6_numeric_order():
    p = problem([("9", 1, 1), ("10", 1, 1)], sc=scenario(id_order="numeric"))
    assert p.id_rank[p.index["9"]] < p.id_rank[p.index["10"]]


def test_I6_numeric_order_rejects_non_numeric_ids():
    with pytest.raises(InputError, match="not an integer"):
        problem([("zone-a", 1, 1)], sc=scenario(id_order="numeric"))


def test_numeric_order_rejects_equal_keys():
    with pytest.raises(InputError, match="same numeric key"):
        problem([("01", 1, 1), ("1", 1, 1)], sc=scenario(id_order="numeric"))


def test_explicit_order():
    sc = scenario(id_order="explicit", id_order_list=["b", "a"])
    p = problem([("a", 1, 1), ("b", 1, 1)], sc=sc)
    assert p.id_rank[p.index["b"]] == 0


def test_undeclared_level_rejected():
    with pytest.raises(InputError, match="not declared"):
        problem([("a", 7, 1)])


def test_unknown_id_in_times_rejected():
    inp = make_inputs([("a", 1, 1)], times={("a", "zz"): 3})
    with pytest.raises(InputError, match="zz"):
        build_problem(inp, scenario())


def test_duplicate_ids_rejected():
    with pytest.raises(InputError, match="duplicate"):
        problem([("a", 1, 1), ("a", None, 1)])
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_problem.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'maps_sll.inputs'`

- [ ] **Step 4: Write `src/maps_sll/inputs.py`**

```python
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


@dataclass
class Inputs:
    units: pd.DataFrame
    contiguity: pd.DataFrame
    times: pd.DataFrame
    times_description: str = "unspecified"
    _fingerprints: dict[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_paths(cls, units, contiguity, times, times_description: str) -> "Inputs":
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
    def from_scenario(cls, scenario: Scenario, base_dir: str | Path) -> "Inputs":
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
    if path.suffix == ".parquet":
        df = pd.read_parquet(path, dtype_backend="pyarrow" if arrow else "numpy_nullable")
    elif path.suffix == ".csv":
        df = pd.read_csv(path, dtype={c: str for c in str_cols})
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
```

- [ ] **Step 5: Write `src/maps_sll/problem.py`**

```python
"""The problem in array form: every unit has a position, every relation an index."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from .inputs import CONTIGUITY_COLUMNS, TIMES_COLUMNS, UNIT_COLUMNS, Inputs
from .scenario import Scenario


class InputError(ValueError):
    """Inputs inconsistent with each other or with the scenario."""


@dataclass
class Problem:
    ids: np.ndarray  # object, str
    names: np.ndarray  # object, str
    level: np.ndarray  # int64, -1 = non-centrality
    strength: np.ndarray  # int64, position in scenario.levels, -1 = non-centrality
    weight: np.ndarray  # float64
    id_rank: np.ndarray  # int64, 0 = first in the declared order
    missing: np.ndarray  # object, passed through to the output
    times: np.ndarray  # float32 n x n, NaN = no time
    neighbours: list[list[tuple[int, float]]]  # (j, shared length / perimeter of i)
    index: dict[str, int]

    @property
    def n(self) -> int:
        return len(self.ids)

    @property
    def is_centrality(self) -> np.ndarray:
        return self.level >= 0

    def is_relevant(self, a: int, b: int, share: float, scenario: Scenario) -> bool:
        """Relevant contiguity (A1, "Contiguità rilevante"): share on the perimeter of `a`,
        time from `a` to `b`; both thresholds strict (decision D15)."""
        t = self.times[a, b]
        return bool(
            share > scenario.contiguity.min_shared_share and t < scenario.contiguity.max_minutes
        )


def build_problem(inputs: Inputs, scenario: Scenario) -> Problem:
    u = inputs.units
    _require(u, UNIT_COLUMNS, "units")
    _require(inputs.contiguity, CONTIGUITY_COLUMNS, "contiguity")
    _require(inputs.times, TIMES_COLUMNS, "travel times")

    ids = u["id"].astype(str).to_numpy(dtype=object)
    if len(set(ids)) != len(ids):
        dup = pd.Series(ids)[pd.Series(ids).duplicated()].unique()[:5]
        raise InputError(f"duplicate unit ids: {list(dup)}")
    n = len(ids)
    index = {uid: i for i, uid in enumerate(ids)}

    lv = pd.to_numeric(u["level"]).astype("Int64")
    has = lv.notna().to_numpy()
    level = np.where(has, lv.fillna(-1).to_numpy(dtype=np.int64), -1)
    undeclared = sorted(set(level[has].tolist()) - set(scenario.levels))
    if undeclared:
        raise InputError(f"levels {undeclared} are not declared in the scenario")
    strength = np.array(
        [scenario.strength(int(x)) if x >= 0 else -1 for x in level], dtype=np.int64
    )

    weight = pd.to_numeric(u["weight"]).to_numpy(dtype=np.float64)
    if np.isnan(weight).any():
        raise InputError("every unit needs a weight")

    names = u["name"].astype(str).to_numpy(dtype=object)
    missing = (
        u["missing"].astype(object).where(u["missing"].notna(), None).to_numpy(dtype=object)
        if "missing" in u
        else np.full(n, None, dtype=object)
    )

    id_values = pa.array(list(ids), type=pa.string())

    c = inputs.contiguity
    o = _codes(c["origin"], id_values, "contiguity origin")
    nb = _codes(c["neighbour"], id_values, "contiguity neighbour")
    share = (
        pd.to_numeric(c["shared_length"]).to_numpy(np.float64)
        / pd.to_numeric(c["origin_perimeter"]).to_numpy(np.float64)
    )
    neighbours: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for a, b, s in zip(o.tolist(), nb.tolist(), share.tolist()):
        if a != b:
            neighbours[a].append((b, s))

    t = inputs.times
    to = _codes(t["origin"], id_values, "travel-time origin")
    td = _codes(t["destination"], id_values, "travel-time destination")
    minutes = t["minutes"].to_numpy(dtype=np.float32, na_value=np.nan)
    if (minutes < 0).any():
        raise InputError("negative travel times")
    times = np.full((n, n), np.nan, dtype=np.float32)
    times[to, td] = minutes
    np.fill_diagonal(times, 0.0)

    return Problem(
        ids=ids,
        names=names,
        level=level,
        strength=strength,
        weight=weight,
        id_rank=_id_rank(ids, scenario),
        missing=missing,
        times=times,
        neighbours=neighbours,
        index=index,
    )


def _require(df: pd.DataFrame, cols: list[str], what: str) -> None:
    absent = [c for c in cols if c not in df.columns]
    if absent:
        raise InputError(f"{what}: missing columns {absent}")


def _codes(col: pd.Series, id_values: pa.Array, what: str) -> np.ndarray:
    arr = pa.array(col.astype(str) if col.dtype.kind in "iuf" else col).cast(pa.string())
    idx = pc.index_in(arr, value_set=id_values)
    if idx.null_count:
        unknown = pc.unique(pc.filter(arr, pc.is_null(idx))).to_pylist()[:5]
        raise InputError(f"{what}: ids not among the units: {unknown}")
    return idx.to_numpy(zero_copy_only=False).astype(np.int64)


def _id_rank(ids: np.ndarray, scenario: Scenario) -> np.ndarray:
    if scenario.id_order == "lexicographic":
        keys = list(ids)
    elif scenario.id_order == "numeric":
        keys = []
        for x in ids:
            try:
                keys.append(int(x))
            except ValueError:
                raise InputError(f"id_order is numeric but id {x!r} is not an integer") from None
        if len(set(keys)) != len(keys):
            raise InputError("id_order is numeric but two ids have the same numeric key")
    else:
        pos = {k: i for i, k in enumerate(scenario.id_order_list or [])}
        absent = [x for x in ids if x not in pos]
        if absent:
            raise InputError(f"ids absent from id_order_list: {absent[:5]}")
        keys = [pos[x] for x in ids]
    order = sorted(range(len(ids)), key=lambda i: keys[i])
    rank = np.empty(len(ids), dtype=np.int64)
    rank[order] = np.arange(len(ids))
    return rank
```

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/pytest tests/test_problem.py`
Expected: `10 passed`

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: inputs and problem arrays with declared id order"
```

---

### Task 4: Label resolution

**Files:**
- Create: `src/maps_sll/labels.py`, `tests/test_labels.py`

- [ ] **Step 1: Write the failing tests `tests/test_labels.py`**

```python
import numpy as np
import pytest

from maps_sll.labels import ChainError, resolve


def test_A4_chain_resolves_to_the_root():
    # 3 -> 2 -> 1 -> 0, 0 is a root
    roots, paths = resolve(np.array([-1, 0, 1, 2]), max_chain_length=16)
    assert roots.tolist() == [0, 0, 0, 0]
    assert paths[3] == [3, 2, 1, 0]


def test_A9_cycle_raises():
    with pytest.raises(ChainError, match="cycle"):
        resolve(np.array([1, 0]), max_chain_length=16, ids=np.array(["a", "b"], dtype=object))


def test_A9_chain_longer_than_declared_raises():
    with pytest.raises(ChainError, match="max_chain_length=2"):
        resolve(np.array([-1, 0, 1, 2]), max_chain_length=2)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_labels.py`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Write `src/maps_sll/labels.py`**

```python
"""Recursive resolution of the attraction label (A1, "Che cosa significa «unita»")."""

from __future__ import annotations

import numpy as np


class ChainError(RuntimeError):
    """A cycle, or a chain longer than the scenario allows (criterion A9)."""


def resolve(
    pointers: np.ndarray, max_chain_length: int, ids: np.ndarray | None = None
) -> tuple[np.ndarray, list[list[int]]]:
    """Follow every pointer to a unit without outgoing pointer.

    Returns the root of every unit and the path from the unit to its root, both ends included.
    """

    def name(k: int) -> str:
        return str(ids[k]) if ids is not None else str(k)

    n = len(pointers)
    roots = np.empty(n, dtype=np.int64)
    paths: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        path = [i]
        seen = {i}
        cur = i
        while pointers[cur] != -1:
            cur = int(pointers[cur])
            if cur in seen:
                raise ChainError(
                    "cycle in the attraction chain: " + " → ".join(name(k) for k in path + [cur])
                )
            path.append(cur)
            seen.add(cur)
            if len(path) - 1 > max_chain_length:
                raise ChainError(
                    f"attraction chain longer than max_chain_length={max_chain_length}: "
                    + " → ".join(name(k) for k in path)
                )
        roots[i] = cur
        paths[i] = path
    return roots, paths
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/pytest tests/test_labels.py`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: chain resolution with cycle and length guard"
```

---

### Task 5: Phase 2

**Files:**
- Create: `src/maps_sll/phase2.py`, `tests/test_phase2.py`

- [ ] **Step 1: Write the failing tests `tests/test_phase2.py`**

```python
from builders import MAPS, problem, scenario
from maps_sll.phase2 import phase2


def merged_to(p, ptr, uid):
    j = ptr[p.index[uid]]
    return None if j == -1 else p.ids[j]


def pair(level_a, w_a, level_b, w_b, share=0.5, minutes=10, sc=None):
    p = problem([("a", level_a, w_a), ("b", level_b, w_b)], [("a", "b", share)],
                {("a", "b"): minutes}, sc=sc)
    return p, phase2(p, sc or scenario())


def test_A6_equal_levels_do_not_merge():
    p, ptr = pair(5, 8000, 5, 9000)
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_A6_toward_weaker_level_does_not_merge():
    p, ptr = pair(4, 30000, 5, 9000)  # 5 -> 4 is not declared, 4 -> 5 is downward
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_A6_undeclared_pair_3_to_2():
    p, ptr = pair(3, 60000, 2, 150000)
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_A6_undeclared_pair_4_to_3():
    p, ptr = pair(4, 30000, 3, 60000)
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_declared_pair_merges():
    p, ptr = pair(5, 8000, 3, 60000)
    assert merged_to(p, ptr, "a") == "b" and merged_to(p, ptr, "b") is None


def test_D15_share_threshold_is_strict():
    p, ptr = pair(5, 8000, 1, 300000, share=0.0309)
    assert merged_to(p, ptr, "a") is None
    p, ptr = pair(5, 8000, 1, 300000, share=0.031)
    assert merged_to(p, ptr, "a") == "b"


def test_D15_time_threshold_is_strict():
    p, ptr = pair(5, 8000, 1, 300000, minutes=20)
    assert merged_to(p, ptr, "a") is None
    p, ptr = pair(5, 8000, 1, 300000, minutes=19)
    assert merged_to(p, ptr, "a") == "b"


def test_share_is_on_the_perimeter_of_the_joining_unit():
    # a joins b: 2% of a's perimeter is shared, 50% of b's
    p = problem([("a", 5, 8000), ("b", 1, 300000)], [("a", "b", 0.02, 0.5)], {("a", "b"): 10})
    assert merged_to(p, phase2(p, scenario()), "a") is None
    p = problem([("a", 5, 8000), ("b", 1, 300000)], [("a", "b", 0.5, 0.02)], {("a", "b"): 10})
    assert merged_to(p, phase2(p, scenario()), "a") == "b"


def test_A7_row_of_minor_centralities_stays_separate():
    p = problem([("a", 4, 30000), ("b", 5, 9000), ("c", 6, 5000)],
                [("a", "b"), ("b", "c")], {("a", "b"): 5, ("b", "c"): 5, ("a", "c"): 10})
    ptr = phase2(p, scenario())
    assert (ptr == -1).all()


def test_A8_prefers_the_stronger_level():
    p = problem([("x", 5, 8000), ("m1", 1, 300000), ("m2", 2, 150000)],
                [("x", "m1"), ("x", "m2")], {("x", "m1"): 15, ("x", "m2"): 5})
    assert merged_to(p, phase2(p, scenario()), "x") == "m1"


def test_A8_equal_level_prefers_greater_weight():
    p = problem([("x", 5, 8000), ("m1", 1, 300000), ("m2", 1, 400000)],
                [("x", "m1"), ("x", "m2")], {("x", "m1"): 5, ("x", "m2"): 15})
    assert merged_to(p, phase2(p, scenario()), "x") == "m2"


def test_A8_equal_level_and_weight_prefers_smaller_id():
    p = problem([("x", 5, 8000), ("m2", 1, 300000), ("m1", 1, 300000)],
                [("x", "m1"), ("x", "m2")], {("x", "m1"): 15, ("x", "m2"): 5})
    assert merged_to(p, phase2(p, scenario()), "x") == "m1"


def test_I3_added_pair_changes_the_result():
    sc = scenario(phase2_pairs={**MAPS["phase2_pairs"], 4: [1, 2, 3]})
    p, ptr = pair(4, 30000, 3, 60000, sc=sc)
    assert merged_to(p, ptr, "a") == "b"


def test_I3_removed_pair_changes_the_result():
    sc = scenario(phase2_pairs={**MAPS["phase2_pairs"], 5: [1, 2]})
    p, ptr = pair(5, 8000, 3, 60000, sc=sc)
    assert merged_to(p, ptr, "a") is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_phase2.py`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Write `src/maps_sll/phase2.py`**

```python
"""Phase 2: merges between contiguous centralities (A1, "Fase 2")."""

from __future__ import annotations

import numpy as np

from .problem import Problem
from .scenario import Scenario


def phase2(p: Problem, scenario: Scenario) -> np.ndarray:
    """Direct step of every centrality toward the main centre it merges into, -1 if none.

    One pass reaches the fixpoint: the candidates of a centrality depend only on level,
    contiguity and times, which phase 2 never changes. Chains come from the resolution.
    """
    ptr = np.full(p.n, -1, dtype=np.int64)
    centrality = p.is_centrality
    for c in np.flatnonzero(centrality):
        allowed = set(scenario.phase2_pairs.get(int(p.level[c]), []))
        if not allowed:
            continue
        best, best_key = -1, None
        for j, share in p.neighbours[c]:
            if not centrality[j] or int(p.level[j]) not in allowed:
                continue
            if not p.is_relevant(c, j, share, scenario):
                continue
            key = (int(p.strength[j]), -float(p.weight[j]), int(p.id_rank[j]))
            if best_key is None or key < best_key:
                best, best_key = j, key
        ptr[c] = best
    return ptr
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/pytest tests/test_phase2.py`
Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: phase 2 merges on declared level pairs"
```

---

### Task 6: Phase 3

**Files:**
- Create: `src/maps_sll/phase3.py`, `tests/test_phase3.py`

- [ ] **Step 1: Write the failing tests `tests/test_phase3.py`**

```python
from builders import problem, scenario
from maps_sll.phase3 import phase3


def attracted_by(p, r, uid):
    j = r.pointers[p.index[uid]]
    return None if j == -1 else p.ids[j]


def test_A3_merged_centrality_keeps_attraction():
    p = problem([("m", 1, 300000), ("s", 3, 60000), ("u", None, 1000)], [("m", "s")],
                {("m", "s"): 10, ("u", "s"): 5, ("u", "m"): 15})
    assert attracted_by(p, phase3(p, scenario()), "u") == "s"


def test_S3_tie_on_time_stronger_level_wins():
    p = problem([("a", 4, 20000), ("b", 5, 30000), ("u", None, 1)],
                times={("u", "a"): 10, ("u", "b"): 10})
    assert attracted_by(p, phase3(p, scenario()), "u") == "a"


def test_S3_tie_on_time_and_level_heavier_wins():
    p = problem([("a", 5, 8000), ("b", 5, 9000), ("u", None, 1)],
                times={("u", "a"): 10, ("u", "b"): 10})
    assert attracted_by(p, phase3(p, scenario()), "u") == "b"


def test_S3_merged_competes_with_its_own_level():
    # s (level 3) is merged into m (level 1); c2 is an unmerged level 2
    p = problem([("m", 1, 300000), ("s", 3, 60000), ("c2", 2, 150000), ("u", None, 1)],
                [("m", "s")],
                {("m", "s"): 10, ("u", "s"): 12, ("u", "c2"): 12, ("u", "m"): 40})
    assert attracted_by(p, phase3(p, scenario()), "u") == "c2"


def test_S3_merged_competes_with_its_own_weight():
    # s (5,000) is merged into m (300,000); t (7,000) heads its own system
    p = problem([("m", 1, 300000), ("s", 5, 5000), ("t", 5, 7000), ("u", None, 1)],
                [("m", "s")], {("m", "s"): 10, ("u", "s"): 10, ("u", "t"): 10, ("u", "m"): 40})
    assert attracted_by(p, phase3(p, scenario()), "u") == "t"


def test_S4_last_tiebreak_follows_declared_id_order():
    units = [("9", 5, 8000), ("10", 5, 8000), ("u", None, 1)]
    times = {("u", "9"): 10, ("u", "10"): 10}
    p = problem(units, times=times)
    assert attracted_by(p, phase3(p, scenario()), "u") == "10"
    sc = scenario(id_order="explicit", id_order_list=["9", "10", "u"])
    p = problem(units, times=times, sc=sc)
    assert attracted_by(p, phase3(p, sc), "u") == "9"


def test_S4_record_order_is_irrelevant():
    units = [("a", 5, 8000), ("b", 5, 8000), ("u", None, 1)]
    times = {("u", "a"): 10, ("u", "b"): 10}
    p1 = problem(units, times=times)
    p2 = problem(list(reversed(units)), times=times)
    assert attracted_by(p1, phase3(p1, scenario()), "u") == attracted_by(
        p2, phase3(p2, scenario()), "u") == "a"


def test_S5_distant_units_are_assigned_and_flagged():
    p = problem([("a", 5, 8000), ("u", None, 1)], times={("u", "a"): 70})
    r = phase3(p, scenario())
    u = p.index["u"]
    assert attracted_by(p, r, "u") == "a" and r.distant[u] and r.minutes[u] == 70


def test_S6_threshold_changes_flags_not_assignment():
    units = [("a", 5, 8000), ("u1", None, 1), ("u2", None, 1)]
    times = {("u1", "a"): 45, ("u2", "a"): 25}
    p = problem(units, times=times)
    r60, r30 = phase3(p, scenario()), phase3(p, scenario(distant_minutes=30))
    assert (r60.pointers == r30.pointers).all()
    assert not r60.distant.any()
    assert r30.distant[p.index["u1"]] and not r30.distant[p.index["u2"]]


def test_R6_unit_without_times_is_unassigned():
    p = problem([("a", 5, 8000), ("u", None, 1)])
    r = phase3(p, scenario())
    assert r.unassigned[p.index["u"]] and r.pointers[p.index["u"]] == -1
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_phase3.py`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Write `src/maps_sll/phase3.py`**

```python
"""Phase 3: assignment of non-centralities (A1, "Fase 3", decisions D21, D22, D1, D2)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .problem import Problem
from .scenario import Scenario


@dataclass
class Phase3Result:
    pointers: np.ndarray  # int64; -1 for centralities and unassigned units
    minutes: np.ndarray  # float64; time to the attracting centrality, NaN otherwise
    distant: np.ndarray  # bool
    unassigned: np.ndarray  # bool; non-centralities without any finite time


def phase3(p: Problem, scenario: Scenario, block: int = 1024) -> Phase3Result:
    n = p.n
    pointers = np.full(n, -1, dtype=np.int64)
    minutes = np.full(n, np.nan)
    cen = np.flatnonzero(p.is_centrality)
    non = np.flatnonzero(~p.is_centrality)
    if cen.size:
        # tie-break rank of every centrality: level, weight (desc), declared id order
        order = np.lexsort((p.id_rank[cen], -p.weight[cen], p.strength[cen]))
        tie = np.empty(cen.size, dtype=np.int64)
        tie[order] = np.arange(cen.size)
        for start in range(0, non.size, block):
            rows = non[start : start + block]
            t = p.times[np.ix_(rows, cen)].astype(np.float64)
            t[np.isnan(t)] = np.inf
            best = t.min(axis=1)
            candidates = np.where(t == best[:, None], tie[None, :], cen.size)
            k = candidates.argmin(axis=1)
            ok = np.isfinite(best)
            pointers[rows[ok]] = cen[k[ok]]
            minutes[rows[ok]] = best[ok]
    unassigned = ~p.is_centrality & (pointers == -1)
    distant = np.nan_to_num(minutes, nan=-np.inf) > scenario.distant_minutes
    return Phase3Result(pointers, minutes, distant, unassigned)
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/pytest tests/test_phase3.py`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: phase 3 assignment with tie-break chain and distant flag"
```

---

### Task 7: Phase 4 and engine

Phase 4 needs the frozen state at the end of phase 3, so its tests run through `engine.run`. Both modules land in this task.

**Files:**
- Create: `src/maps_sll/phase4.py`, `src/maps_sll/engine.py`, `tests/test_phase4.py`
- Modify: `tests/builders.py` (uncomment `run_case`, `step`, `system_of` and the engine import)

- [ ] **Step 1: Uncomment in `tests/builders.py` the line `from maps_sll.engine import run` and the functions `run_case`, `step`, `system_of`**

- [ ] **Step 2: Write the failing tests `tests/test_phase4.py`**

```python
from builders import ix, run_case, scenario, step, system_of


def case1(w_s):
    # s: single-unit system, level 6; h: level 4, heads a system with u
    return run_case([("s", 6, w_s), ("h", 4, 15000), ("u", None, 1000)], [("s", "h")],
                    {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30})


def test_A12_case1_heavier_single_becomes_the_centre():
    r = case1(20000)
    assert step(r, "h") == "s" and system_of(r, "u") == "s" and system_of(r, "s") == "s"
    h = ix(r.problem, "h")
    assert r.rule[h] == "P4-CLAIMED" and r.problem.level[h] == 4  # still a centrality
    assert r.phase4.changed_heads == [(h, ix(r.problem, "s"))]  # metric V10


def test_A12_case2_lighter_single_joins_as_merged_centre():
    r = case1(10000)
    assert step(r, "s") == "h" and system_of(r, "s") == "h"
    assert r.rule[ix(r.problem, "s")] == "P4-JOIN"


def test_A11_phase4_does_not_touch_phase3_assignments():
    for w in (20000, 10000):
        r = case1(w)
        non = ~r.problem.is_centrality
        assert (r.ptr3[non] == r.ptr4[non]).all()


def test_A12_case3_single_of_level_2_starts_no_merge():
    r = run_case([("x", 2, 150000), ("h3", 3, 60000), ("u", None, 1000)], [("x", "h3")],
                 {("x", "h3"): 10, ("u", "h3"): 5, ("u", "x"): 30})
    assert step(r, "x") is None and step(r, "h3") is None
    assert r.rule[ix(r.problem, "x")] == "HEAD"


def case4(w_s):
    # a (level 5) merges into T (level 3) in phase 2; s is contiguous only to a
    return run_case([("T", 3, 60000), ("a", 5, 8000), ("s", 6, w_s)], [("a", "T"), ("s", "a")],
                    {("a", "T"): 10, ("s", "a"): 8, ("s", "T"): 25})


def test_A12_case4_lighter_than_merged_neighbour_enters_its_system():
    r = case4(5000)
    assert step(r, "s") == "a" and system_of(r, "s") == "T" and step(r, "a") == "T"


def test_A12_case4_heavier_than_merged_neighbour_stays_alone():
    r = case4(9000)
    assert step(r, "s") is None and step(r, "a") == "T"
    assert r.rule[ix(r.problem, "s")] == "P4-ALONE"


def test_A12_case5_compares_with_the_nearest_even_if_less_populous():
    r = run_case(
        [("s", 6, 10000), ("n", 5, 12000), ("f", 4, 40000), ("u1", None, 1), ("u2", None, 1)],
        [("s", "n"), ("s", "f")],
        {("s", "n"): 5, ("s", "f"): 15, ("u1", "n"): 2, ("u1", "f"): 50, ("u1", "s"): 30,
         ("u2", "f"): 2, ("u2", "n"): 50, ("u2", "s"): 30},
    )
    assert step(r, "s") == "n"


def test_A12_case6_level4_joins_single_unit_level3():
    r = run_case([("s", 4, 30000), ("t", 3, 60000)], [("s", "t")], {("s", "t"): 10})
    assert step(r, "s") == "t" and r.rule[ix(r.problem, "s")] == "P4-D25"


def test_D25_non_eligible_single_wins_regardless_of_weight():
    r = run_case([("s", 4, 30000), ("t", 3, 20000)], [("s", "t")], {("s", "t"): 10})
    assert step(r, "s") == "t"


def case7(w_y):
    # a (level 5) merged into T; y heads a system with u; s nearer to a than to y
    return run_case(
        [("T", 3, 60000), ("a", 5, 8000), ("s", 6, 20000), ("y", 4, w_y), ("u", None, 1)],
        [("a", "T"), ("s", "a"), ("s", "y")],
        {("a", "T"): 10, ("s", "a"): 5, ("s", "y"): 10, ("u", "y"): 3, ("u", "s"): 30,
         ("u", "a"): 40, ("u", "T"): 40},
    )


def test_A12_case7_heavier_than_y_becomes_its_centre():
    r = case7(15000)
    assert step(r, "y") == "s" and system_of(r, "u") == "s" and system_of(r, "s") == "s"


def test_A12_case7_lighter_than_y_joins_y():
    r = case7(25000)
    assert step(r, "s") == "y" and system_of(r, "s") == "y"


def test_determinism_own_choice_prevails_over_a_claim():
    # c chooses d (heavier); s (heavier than c) claims c: the claim has no effect
    r = run_case(
        [("c", 6, 10000), ("d", 5, 20000), ("s", 6, 15000), ("u", None, 1)],
        [("c", "d"), ("c", "s")],
        {("c", "d"): 5, ("c", "s"): 8, ("u", "d"): 3, ("u", "c"): 30, ("u", "s"): 30},
    )
    assert step(r, "c") == "d" and step(r, "s") is None
    assert r.rule[ix(r.problem, "s")] == "P4-CLAIM-IGNORED"


def test_several_claimants_the_heaviest_wins():
    r = run_case(
        [("h", 5, 10000), ("s1", 6, 15000), ("s2", 6, 18000), ("u", None, 1)],
        [("s1", "h"), ("s2", "h")],
        {("s1", "h"): 5, ("s2", "h"): 6, ("u", "h"): 2, ("u", "s1"): 30, ("u", "s2"): 30},
    )
    assert step(r, "h") == "s2" and system_of(r, "u") == "s2"
    assert r.rule[ix(r.problem, "s1")] == "P4-CLAIM-LOST"


def test_I4_phase4_levels_are_declared_in_the_scenario():
    units = [("s", 6, 10000), ("h", 4, 15000), ("u", None, 1000)]
    times = {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30}
    r = run_case(units, [("s", "h")], times, sc=scenario(phase4_levels=[4, 5]))
    assert step(r, "s") is None and r.rule[ix(r.problem, "s")] == "HEAD"


def test_I4_four_level_scheme():
    sc = scenario(levels=[1, 2, 3, 4], phase2_pairs={2: [1], 3: [1, 2]}, phase4_levels=[3, 4])
    r = run_case([("s", 4, 10000), ("h", 3, 15000), ("u", None, 1000)], [("s", "h")],
                 {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30}, sc=sc)
    assert step(r, "s") == "h"
```

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_phase4.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'maps_sll.engine'`

- [ ] **Step 4: Write `src/maps_sll/phase4.py`**

```python
"""Phase 4: single-unit systems (A1, "Fase 4", decisions D13, D23-D26; design 6.6)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .problem import Problem
from .scenario import Scenario


@dataclass
class Phase4Result:
    pointers: np.ndarray  # phase-3 pointers plus the phase-4 steps between centralities
    rules: dict[int, str] = field(default_factory=dict)  # centrality -> P4-* rule
    ignored_claims: list[tuple[int, int]] = field(default_factory=list)  # (claimant, claimed)
    changed_heads: list[tuple[int, int]] = field(default_factory=list)  # (old centre, new) V10


def phase4(p: Problem, scenario: Scenario, ptr3: np.ndarray) -> Phase4Result:
    centrality = p.is_centrality
    incoming = np.bincount(ptr3[ptr3 >= 0], minlength=p.n)
    single = centrality & (ptr3 == -1) & (incoming == 0)
    eligible = set(scenario.phase4_levels)

    def heavier(a: int, b: int) -> bool:
        return (p.weight[a], -p.id_rank[a]) > (p.weight[b], -p.id_rank[b])

    joins: dict[int, int] = {}
    claims: dict[int, list[int]] = {}
    rules: dict[int, str] = {}
    for s in sorted(np.flatnonzero(single).tolist(), key=lambda i: p.id_rank[i]):
        if int(p.level[s]) not in eligible:
            continue
        candidates = sorted(
            (float(p.times[s, j]), -float(p.weight[j]), int(p.id_rank[j]), j)
            for j, share in p.neighbours[s]
            if j != s and centrality[j] and p.is_relevant(s, j, share, scenario)
        )
        outcome = "P4-ALONE"
        for *_, j in candidates:
            if single[j] and int(p.level[j]) not in eligible:
                joins[s], outcome = j, "P4-D25"
                break
            if heavier(j, s):
                joins[s], outcome = j, "P4-JOIN"
                break
            if ptr3[j] != -1:  # merged and lighter: no effect, next candidate (D23, D26)
                continue
            claims.setdefault(j, []).append(s)
            outcome = "P4-CLAIM"
            break
        rules[s] = outcome

    pointers = ptr3.copy()
    for s, j in joins.items():
        pointers[s] = j
    result = Phase4Result(pointers, rules)
    for j, claimants in sorted(claims.items()):
        winner = max(claimants, key=lambda a: (p.weight[a], -p.id_rank[a]))
        if j in joins:  # its own choice prevails (design, paragraph 6.6)
            for a in claimants:
                rules[a] = "P4-CLAIM-IGNORED"
                result.ignored_claims.append((a, j))
            continue
        for a in claimants:
            if a != winner:
                rules[a] = "P4-CLAIM-LOST"
        pointers[j] = winner
        rules[j] = "P4-CLAIMED"
        if incoming[j] > 0:
            result.changed_heads.append((j, winner))
    return result
```

- [ ] **Step 5: Write `src/maps_sll/engine.py`**

```python
"""Execution of phases 2-4 and label resolution."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np

from .inputs import Inputs
from .labels import resolve
from .phase2 import phase2
from .phase3 import phase3
from .phase4 import Phase4Result, phase4
from .problem import Problem, build_problem
from .scenario import Scenario


@dataclass
class Result:
    scenario: Scenario
    inputs: Inputs
    problem: Problem
    ptr2: np.ndarray
    ptr3: np.ndarray
    ptr4: np.ndarray
    minutes: np.ndarray  # time to the direct step
    distant: np.ndarray
    unassigned: np.ndarray
    phase: np.ndarray  # 2, 3 or 4
    rule: np.ndarray  # object
    roots: np.ndarray
    paths: list[list[int]]
    phase4: Phase4Result
    timings: dict[str, float]


def run(scenario: Scenario, inputs: Inputs) -> Result:
    timings: dict[str, float] = {}

    def timed(name, fn, *args):
        t = perf_counter()
        out = fn(*args)
        timings[name] = perf_counter() - t
        return out

    p = timed("build_problem", build_problem, inputs, scenario)
    ptr2 = timed("phase2", phase2, p, scenario)
    r3 = timed("phase3", phase3, p, scenario)
    ptr3 = np.where(p.is_centrality, ptr2, r3.pointers)
    r4 = timed("phase4", phase4, p, scenario, ptr3)
    roots, paths = timed("resolve", resolve, r4.pointers, scenario.max_chain_length, p.ids)
    timings["core"] = sum(timings[k] for k in ("phase2", "phase3", "phase4", "resolve"))

    ptr4 = r4.pointers
    minutes = r3.minutes.copy()
    merged = np.flatnonzero(p.is_centrality & (ptr4 >= 0))
    minutes[merged] = p.times[merged, ptr4[merged]]

    phase = np.full(p.n, 3, dtype=np.int64)
    rule = np.full(p.n, "P3-NEAREST", dtype=object)
    rule[r3.unassigned] = "UNASSIGNED"
    for c in np.flatnonzero(p.is_centrality):
        phase[c] = 2
        rule[c] = "P2-MERGE" if ptr2[c] >= 0 else "HEAD"
    for c, rr in r4.rules.items():
        phase[c] = 4
        rule[c] = rr

    return Result(
        scenario=scenario, inputs=inputs, problem=p, ptr2=ptr2, ptr3=ptr3, ptr4=ptr4,
        minutes=minutes, distant=r3.distant, unassigned=r3.unassigned, phase=phase, rule=rule,
        roots=roots, paths=paths, phase4=r4, timings=timings,
    )
```

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/pytest`
Expected: all pass (`tests/test_phase4.py`: `15 passed`)

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: phase 4 and engine"
```

---

### Task 8: Output tables and engine-level properties

**Files:**
- Create: `src/maps_sll/output.py` (tables only), `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests `tests/test_engine.py`**

```python
import numpy as np
import pandas as pd
import pytest

from builders import make_inputs, run_case, scenario
from maps_sll.engine import run
from maps_sll.output import systems_table, units_table
from maps_sll.problem import InputError

MILANO = (
    [("M", 1, 300000, "Milano"), ("S", 3, 80000, "Sesto San Giovanni"),
     ("X", 5, 9000, "Xtown"), ("u", None, 500, "Ucomune")],
    [("M", "S"), ("S", "X")],
    {("M", "S"): 10, ("S", "X"): 8, ("u", "X"): 3, ("u", "S"): 15, ("u", "M"): 25,
     ("X", "M"): 18},
)


def row(df, uid):
    return df.set_index("id").loc[uid]


def test_A4_A5_three_step_chain_and_labels():
    t = units_table(run_case(*MILANO))
    u = row(t, "u")
    assert u.system_id == "M"
    assert u.full_label == "Milano(Xtown)"
    assert u.chain == "Xtown → Sesto San Giovanni → Milano"
    assert row(t, "S").full_label == "Milano(Sesto San Giovanni)"


def test_A1_centralities_unchanged():
    r = run_case(*MILANO)
    t = units_table(r)
    assert int(t.level.notna().sum()) == 3
    assert t[t.level.notna()].set_index("id").level.to_dict() == {"M": 1, "S": 3, "X": 5}


def test_A2_one_system_less_per_merge():
    r = run_case(*MILANO)
    merges = int((r.ptr2 >= 0).sum())
    assert len(systems_table(r)) == int(r.problem.is_centrality.sum()) - merges == 1


def test_S2_merged_centrality_keeps_its_nature():
    s = row(units_table(run_case(*MILANO)), "S")
    assert s.level == 3 and s.role == "merged_centre" and s.system_id == "M"
    m = row(units_table(run_case(*MILANO)), "M")
    assert m.role == "main_centre" and m.system_id == "M"


def test_S8_every_system_is_headed_by_an_unmerged_centrality():
    r = run_case(*MILANO)
    t = units_table(r)
    heads = t.set_index("id").loc[t.system_id.unique()]
    assert (heads.role == "main_centre").all() and heads.direct_step_id.isna().all()


def test_S3_merged_winner_brings_the_unit_into_the_main_centre_system():
    r = run_case([("m", 1, 300000), ("s", 3, 60000), ("u", None, 1)], [("m", "s")],
                 {("m", "s"): 10, ("u", "s"): 5, ("u", "m"): 15})
    u = row(units_table(r), "u")
    assert u.direct_step_id == "s" and u.system_id == "m"


def test_O1b_phase_and_rule_on_every_row():
    t = units_table(run_case(*MILANO))
    assert t.phase.notna().all() and t.rule.notna().all()
    assert row(t, "S").rule == "P2-MERGE" and row(t, "u").rule == "P3-NEAREST"


def test_O2_O3_unique_units_and_weight_sums():
    r = run_case(*MILANO)
    t, s = units_table(r), systems_table(r)
    assert t.id.is_unique
    assert s.set_index("system_id").total_weight["M"] == 300000 + 80000 + 9000 + 500


def test_R1_two_runs_same_output():
    pd.testing.assert_frame_equal(units_table(run_case(*MILANO)), units_table(run_case(*MILANO)))


def test_R4_record_order_does_not_matter():
    inp = make_inputs(*MILANO)
    r1 = run(scenario(), inp)
    shuffled = make_inputs(*MILANO)
    for name in ("units", "contiguity", "times"):
        df = getattr(shuffled, name)
        setattr(shuffled, name, df.sample(frac=1, random_state=3).reset_index(drop=True))
    r2 = run(scenario(), shuffled)
    pd.testing.assert_frame_equal(units_table(r1), units_table(r2))
    for attr in ("ptr2", "ptr3", "ptr4"):
        a = {r1.problem.ids[i]: getattr(r1, attr)[i] for i in range(r1.problem.n)}
        b = {r2.problem.ids[i]: getattr(r2, attr)[i] for i in range(r2.problem.n)}
        ida = {k: (r1.problem.ids[v] if v >= 0 else None) for k, v in a.items()}
        idb = {k: (r2.problem.ids[v] if v >= 0 else None) for k, v in b.items()}
        assert ida == idb


def test_I1_runs_on_levels_only():
    inp = make_inputs(*MILANO)
    assert list(inp.units.columns) == ["id", "name", "level", "weight"]
    assert len(units_table(run(scenario(), inp))) == 4


def test_I2_seven_levels_without_code_changes():
    sc = scenario(levels=[1, 2, 3, 4, 5, 6, 7],
                  phase2_pairs={2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3], 6: [1, 2, 3],
                                7: [1, 2, 3]},
                  phase4_levels=[4, 5, 6, 7])
    r = run_case([("a", 7, 1000), ("b", 3, 60000)], [("a", "b")], {("a", "b"): 5}, sc=sc)
    assert row(units_table(r), "a").system_id == "b"


def test_I2_five_levels_without_code_changes():
    sc = scenario(levels=[1, 2, 3, 4, 5],
                  phase2_pairs={2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3]},
                  phase4_levels=[4, 5])
    r = run_case([("a", 5, 1000), ("b", 3, 60000)], [("a", "b")], {("a", "b"): 5}, sc=sc)
    assert row(units_table(r), "a").system_id == "b"


def synthetic(n=200, seed=7):
    rng = np.random.default_rng(seed)
    side = int(np.ceil(np.sqrt(n)))
    ids = [f"zone-{chr(97 + i % 26)}{i:03d}" for i in range(n)]
    pos = {uid: (i % side, i // side) for i, uid in enumerate(ids)}
    levels = [None] * n
    for i in rng.choice(n, 40, replace=False):
        levels[i] = int(rng.integers(1, 7))
    units = [(ids[i], levels[i], int(rng.integers(100, 300000))) for i in range(n)]
    contig = []
    for i, a in enumerate(ids):
        x, y = pos[a]
        for b in ids[i + 1:]:
            bx, by = pos[b]
            if abs(bx - x) + abs(by - y) == 1:
                contig.append((a, b, float(rng.uniform(0.01, 0.3)), float(rng.uniform(0.01, 0.3))))
    times = {}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            (ax, ay), (bx, by) = pos[a], pos[b]
            times[(a, b)] = float(round(6 * np.hypot(ax - bx, ay - by)))
    return units, contig, times


def test_I6_synthetic_units_with_non_istat_ids():
    r = run_case(*synthetic())
    t = units_table(r)
    assert len(t) == 200 and t.id.is_unique
    heads = t.set_index("id").loc[t.system_id.unique()]
    assert (heads.role == "main_centre").all()


def test_I6_engine_does_not_assume_numeric_ids():
    with pytest.raises(InputError, match="not an integer"):
        run_case(*synthetic(), sc=scenario(id_order="numeric"))
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_engine.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'maps_sll.output'`

- [ ] **Step 3: Write `src/maps_sll/output.py` (tables part)**

```python
"""Output tables (A1, "Output")."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import Result

UNIT_OUTPUT_COLUMNS = [
    "id", "name", "level", "missing", "direct_step_id", "system_id", "system_name",
    "full_label", "chain", "role", "minutes", "distant", "phase", "rule",
]
SYSTEM_OUTPUT_COLUMNS = [
    "system_id", "name", "main_centre_id", "main_centre_level", "n_units", "total_weight",
    "merged_centres_phase2", "merged_centres_phase4", "max_chain_length",
]


def units_table(r: Result) -> pd.DataFrame:
    """One row per unit present in the travel-time matrix, in declared id order."""
    p = r.problem
    rows = []
    assigned = sorted(np.flatnonzero(~r.unassigned).tolist(), key=lambda k: p.id_rank[k])
    for i in assigned:
        root, step, cen = int(r.roots[i]), int(r.ptr4[i]), bool(p.is_centrality[i])
        if cen and step == -1:
            role, full = "main_centre", p.names[root]
        elif cen:
            role, full = "merged_centre", f"{p.names[root]}({p.names[i]})"
        else:
            role = "attracted"
            full = p.names[root] if step == root else f"{p.names[root]}({p.names[step]})"
        chain_ids = r.paths[i] if cen else r.paths[i][1:]
        rows.append({
            "id": p.ids[i],
            "name": p.names[i],
            "level": int(p.level[i]) if p.level[i] >= 0 else None,
            "missing": p.missing[i],
            "direct_step_id": p.ids[step] if step >= 0 else None,
            "system_id": p.ids[root],
            "system_name": p.names[root],
            "full_label": full,
            "chain": " → ".join(p.names[k] for k in chain_ids),
            "role": role,
            "minutes": float(r.minutes[i]),
            "distant": bool(r.distant[i]),
            "phase": int(r.phase[i]),
            "rule": r.rule[i],
        })
    df = pd.DataFrame(rows, columns=UNIT_OUTPUT_COLUMNS)
    df["level"] = df["level"].astype("Int64")
    return df


def systems_table(r: Result, units: pd.DataFrame | None = None) -> pd.DataFrame:
    p = r.problem
    units = units_table(r) if units is None else units
    depth = {p.ids[i]: len(r.paths[i]) - 1 for i in np.flatnonzero(p.is_centrality)}
    rows = []
    for sid, g in units.groupby("system_id", sort=False):
        merged = g[g.role == "merged_centre"]
        head = p.index[sid]
        rows.append({
            "system_id": sid,
            "name": p.names[head],
            "main_centre_id": sid,
            "main_centre_level": int(p.level[head]),
            "n_units": len(g),
            "total_weight": float(sum(p.weight[p.index[x]] for x in g.id)),
            "merged_centres_phase2": int((merged.phase == 2).sum()),
            "merged_centres_phase4": int((merged.phase == 4).sum()),
            "max_chain_length": max(depth.get(x, 0) for x in g.id),
        })
    df = pd.DataFrame(rows, columns=SYSTEM_OUTPUT_COLUMNS)
    order = df.system_id.map(lambda x: p.id_rank[p.index[x]])
    return df.iloc[np.argsort(order.to_numpy(), kind="stable")].reset_index(drop=True)


def distant_table(units: pd.DataFrame) -> pd.DataFrame:
    """Criterion S7: distant units as a dataset of their own."""
    cols = ["id", "name", "system_id", "system_name", "minutes"]
    return units.loc[units.distant, cols].reset_index(drop=True)


def unassigned_table(r: Result) -> pd.DataFrame:
    """Criterion R6: units without travel times."""
    p = r.problem
    idx = sorted(np.flatnonzero(r.unassigned).tolist(), key=lambda k: p.id_rank[k])
    return pd.DataFrame({"id": [p.ids[i] for i in idx], "name": [p.names[i] for i in idx]})
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/pytest`
Expected: all pass (`tests/test_engine.py`: `16 passed`)

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: units and systems tables; engine-level criteria tests"
```

---

### Task 9: Metrics, manifest, writing the outputs, CLI

**Files:**
- Create: `src/maps_sll/metrics.py`, `src/maps_sll/manifest.py`, `src/maps_sll/cli.py`, `tests/test_outputs.py`
- Modify: `src/maps_sll/output.py` (append `write_outputs`)

- [ ] **Step 1: Write the failing tests `tests/test_outputs.py`**

```python
import json

import yaml

from builders import make_inputs, run_case, scenario
from maps_sll.cli import main
from maps_sll.engine import run
from maps_sll.metrics import compute_metrics
from maps_sll.output import systems_table, units_table, write_outputs

CASE = (
    [("M", 1, 300000), ("u1", None, 1000), ("u2", None, 2000), ("far", None, 500)],
    [("M", "u1")],
    {("u1", "M"): 10, ("u2", "M"): 15, ("far", "M"): 75},
)


def test_I7_structural_metrics_without_comparison_data():
    r = run_case(*CASE)
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert set(m) == {"V2", "V3", "V4", "V5", "V9", "V10"}


def test_V4_share_within_threshold():
    r = run_case(*CASE)
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert m["V4"]["n_distant"] == 1
    assert abs(m["V4"]["weight_share_within"] - 303000 / 303500) < 1e-12


def test_V5_non_contiguous_system_is_listed():
    r = run_case(*CASE)
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert m["V5"]["n_non_contiguous_systems"] == 1
    assert m["V5"]["cases"][0]["isolated_ids"] == ["far", "u2"]


def test_O5_outputs_written(tmp_path):
    r = run_case(*CASE)
    write_outputs(r, tmp_path, started_at="2026-11-05T10:00:00+00:00")
    for name in ("units", "systems", "distant", "unassigned"):
        assert (tmp_path / f"{name}.parquet").exists() and (tmp_path / f"{name}.csv").exists()
    assert (tmp_path / "metrics.json").exists()
    # O5: the scenario travels with the output
    sc = yaml.safe_load((tmp_path / "scenario.yaml").read_text(encoding="utf-8"))
    assert sc["name"] == "test-maps"


def test_R5_A10_O6_P2_manifest(tmp_path):
    r = run_case(*CASE)
    write_outputs(r, tmp_path, started_at="2026-11-05T10:00:00+00:00")
    m = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert m["package_version"] and "git_commit" in m
    assert set(m["inputs"]) == {"units", "contiguity", "travel_times"}
    assert m["reference_year"] == 2025
    assert m["thresholds_used"] == {"min_shared_share": 0.0309, "max_minutes": 20.0,
                                    "distant_minutes": 60.0}
    assert m["travel_times"]["description"] == "test matrix"
    assert {"phase2", "phase3", "phase4", "resolve", "core", "write_tables"} <= set(
        m["timings_seconds"])


def test_O6_two_matrices_are_distinguishable():
    units, contig, times = CASE
    r1 = run(scenario(), make_inputs(units, contig, times))
    r2 = run(scenario(), make_inputs(units, contig, {**times, ("u2", "M"): 16}))
    assert (r1.inputs.fingerprints()["travel_times"]
            != r2.inputs.fingerprints()["travel_times"])


def test_S7_distant_dataset(tmp_path):
    write_outputs(run_case(*CASE), tmp_path, started_at="x")
    import pandas as pd
    d = pd.read_csv(tmp_path / "distant.csv", dtype={"id": str})
    assert d.id.tolist() == ["far"] and d.system_id.tolist() == ["M"]


def test_cli_run(tmp_path):
    units, contig, times = CASE
    inp = make_inputs(units, contig, times)
    inp.units.to_csv(tmp_path / "units.csv", index=False)
    inp.contiguity.to_csv(tmp_path / "contiguity.csv", index=False)
    inp.times.to_csv(tmp_path / "times.csv", index=False)
    sc = scenario().model_dump(mode="json")
    sc["inputs"] = {"units": "units.csv", "contiguity": "contiguity.csv",
                    "travel_times": {"path": "times.csv", "description": "csv test"}}
    (tmp_path / "s.yaml").write_text(yaml.safe_dump(sc), encoding="utf-8")
    assert main(["run", str(tmp_path / "s.yaml"), "--out", str(tmp_path / "out")]) == 0
    m = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert m["inputs"]["travel_times"].startswith("sha256:")
    assert "read_inputs" in m["timings_seconds"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_outputs.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'maps_sll.metrics'`

- [ ] **Step 3: Write `src/maps_sll/metrics.py`**

```python
"""Structural metrics V2-V5, V9, V10 (D3.2.1, "Misure strutturali")."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .engine import Result

BINS = [0, 1, 5, 10, 20, 50, np.inf]
BIN_LABELS = ["1", "2-5", "6-10", "11-20", "21-50", "51+"]


def _quantiles(s: pd.Series) -> dict[str, float]:
    if s.empty:
        return {}
    q = s.quantile([0, 0.25, 0.5, 0.75, 1])
    return {f"p{int(k * 100)}": float(v) for k, v in q.items()}


def compute_metrics(r: Result, units: pd.DataFrame, systems: pd.DataFrame) -> dict:
    p = r.problem
    hist = (
        pd.cut(systems.n_units, bins=BINS, labels=BIN_LABELS)
        .value_counts()
        .reindex(BIN_LABELS, fill_value=0)
    )
    single = systems[systems.n_units == 1]
    weight = {uid: float(p.weight[p.index[uid]]) for uid in units.id}
    total = sum(weight.values())
    within = sum(weight[uid] for uid in units.id[~units.distant])
    return {
        "V2": {
            "n_systems": int(len(systems)),
            "units_per_system": _quantiles(systems.n_units),
            "weight_per_system": _quantiles(systems.total_weight),
            "units_per_system_histogram": {k: int(v) for k, v in hist.items()},
        },
        "V3": {
            "n_single_unit_systems": int(len(single)),
            "by_centre_level": {
                str(k): int(v)
                for k, v in single.main_centre_level.value_counts().sort_index().items()
            },
        },
        "V4": {
            "distant_minutes": float(r.scenario.distant_minutes),
            "weight_share_within": within / total if total else None,
            "n_distant": int(units.distant.sum()),
        },
        "V5": _non_contiguous(r, units),
        "V9": {
            "max_merged_centres_phase2": int(systems.merged_centres_phase2.max()) if len(systems) else 0,
            "max_merged_centres_phase4": int(systems.merged_centres_phase4.max()) if len(systems) else 0,
            "n_systems_with_merged_centres": int(
                ((systems.merged_centres_phase2 + systems.merged_centres_phase4) > 0).sum()
            ),
            "max_chain_length": int(systems.max_chain_length.max()) if len(systems) else 0,
        },
        "V10": {
            "n_centre_changes": len(r.phase4.changed_heads),
            "cases": [
                {"previous_centre_id": p.ids[h], "new_centre_id": p.ids[s]}
                for h, s in r.phase4.changed_heads
            ],
        },
    }


def _non_contiguous(r: Result, units: pd.DataFrame) -> dict:
    """V5: systems whose units are not all connected to the main centre by contiguity."""
    p = r.problem
    adjacency: dict[int, set[int]] = defaultdict(set)
    for i, nbrs in enumerate(p.neighbours):
        for j, _ in nbrs:
            adjacency[i].add(j)
            adjacency[j].add(i)
    cases = []
    for sid, g in units.groupby("system_id", sort=False):
        members = {p.index[x] for x in g.id}
        start = p.index[sid]
        seen, stack = {start}, [start]
        while stack:
            k = stack.pop()
            for j in adjacency[k]:
                if j in members and j not in seen:
                    seen.add(j)
                    stack.append(j)
        if len(seen) < len(members):
            isolated = sorted(members - seen, key=lambda k: p.id_rank[k])
            cases.append({"system_id": sid, "isolated_ids": [p.ids[k] for k in isolated]})
    cases.sort(key=lambda c: p.id_rank[p.index[c["system_id"]]])
    return {"n_non_contiguous_systems": len(cases), "cases": cases}
```

- [ ] **Step 4: Write `src/maps_sll/manifest.py`**

```python
"""Run manifest (A1, "Manifesto dell'esecuzione"; criteria R5, A10, O5, O6, P2)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .engine import Result


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent,
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_manifest(r: Result, *, started_at: str, extra: dict | None = None) -> dict:
    sc, p = r.scenario, r.problem
    fingerprints = r.inputs.fingerprints()
    manifest = {
        "package": "maps-sll",
        "package_version": __version__,
        "git_commit": _git_commit(),
        "scenario": sc.model_dump(mode="json"),
        "reference_year": sc.reference_year,
        "inputs": fingerprints,
        "travel_times": {
            "description": r.inputs.times_description,
            "fingerprint": fingerprints["travel_times"],
        },
        "thresholds_used": {
            "min_shared_share": sc.contiguity.min_shared_share,
            "max_minutes": sc.contiguity.max_minutes,
            "distant_minutes": sc.distant_minutes,
        },
        "counts": {
            "units": int(p.n),
            "centralities": int(p.is_centrality.sum()),
            "unassigned": int(r.unassigned.sum()),
            "systems": int(len(set(r.roots[~r.unassigned].tolist()))),
        },
        "phase4_centre_changes": len(r.phase4.changed_heads),
        "phase4_ignored_claims": [
            {"claimant": p.ids[a], "claimed": p.ids[b]} for a, b in r.phase4.ignored_claims
        ],
        "timings_seconds": dict(r.timings),
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if extra:
        manifest["extra"] = extra
    return manifest
```

- [ ] **Step 5: Append `write_outputs` to `src/maps_sll/output.py`**

```python
import json
from pathlib import Path
from time import perf_counter

import yaml


def write_outputs(r: Result, out_dir, *, started_at: str, extra: dict | None = None) -> Path:
    from .manifest import build_manifest
    from .metrics import compute_metrics

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t = perf_counter()
    units = units_table(r)
    systems = systems_table(r, units)
    tables = {
        "units": units,
        "systems": systems,
        "distant": distant_table(units),
        "unassigned": unassigned_table(r),
    }
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        df.to_csv(out / f"{name}.csv", index=False)
    metrics = compute_metrics(r, units, systems)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
    (out / "scenario.yaml").write_text(
        yaml.safe_dump(r.scenario.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    r.timings["write_tables"] = perf_counter() - t
    manifest = build_manifest(r, started_at=started_at, extra=extra)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    return out
```

Move the new imports (`json`, `Path`, `perf_counter`, `yaml`) to the top of the module with the others.

- [ ] **Step 6: Write `src/maps_sll/cli.py`**

```python
"""Command line: maps-sll run | levels."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from .engine import run
from .inputs import Inputs
from .output import write_outputs
from .scenario import load_scenario


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="maps-sll")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run phases 2-4 on a scenario")
    r.add_argument("scenario")
    r.add_argument("--out", required=True)
    r.add_argument("--manifest-extra", help="JSON file copied into the manifest under 'extra'")
    lv = sub.add_parser("levels", help="phase 1: assign levels from attributes")
    lv.add_argument("rules")
    lv.add_argument("attributes")
    lv.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "run":
        started = datetime.now(UTC).isoformat(timespec="seconds")
        scenario_path = Path(args.scenario)
        scenario = load_scenario(scenario_path)
        t = perf_counter()
        inputs = Inputs.from_scenario(scenario, scenario_path.parent)
        read_s = perf_counter() - t
        result = run(scenario, inputs)
        result.timings["read_inputs"] = read_s
        extra = (
            json.loads(Path(args.manifest_extra).read_text(encoding="utf-8"))
            if args.manifest_extra
            else None
        )
        write_outputs(result, args.out, started_at=started, extra=extra)
        print(f"{scenario.name}: {result.problem.n} units, "
              f"{int(result.unassigned.sum())} unassigned, output in {args.out}")
        return 0

    from .levels import assign_levels_file

    assign_levels_file(args.rules, args.attributes, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run the tests**

Run: `.venv/bin/pytest tests/test_outputs.py`
Expected: `9 passed`. (`test_cli_run` does not touch the `levels` branch, which arrives in Task 10.)

- [ ] **Step 8: Run the whole suite and ruff**

Run: `.venv/bin/pytest && .venv/bin/ruff check src tests`
Expected: all pass, `All checks passed!`

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: metrics, manifest, output writing and CLI"
```

---

### Task 10: Level calculation (phase 1)

**Files:**
- Create: `src/maps_sll/levels.py`, `maps/levels/maps-rules.yaml`, `tests/test_levels.py`

- [ ] **Step 1: Write `maps/levels/maps-rules.yaml`**

```yaml
# Phase 1 parametrisation in use for MAPS (D3.2.1 appendix A1, "Regole di livello";
# decisions D4, D7, D16). Rules are evaluated in order; the first that applies wins.
# Attributes per unit: population; n_health (health facilities of any kind, DEA included);
# n_dea (DEA of first or second level); n_secondary_schools (upper-secondary schools);
# station_category (highest RFI category of the stations in the unit).
ordinal_attributes:
  station_category: [bronze, silver, gold, platinum]
rules:
  - {id: L1, level: 1, all: [{attr: population, op: ">=", value: 250000}]}
  - {id: L2, level: 2, all: [{attr: population, op: ">=", value: 100000}]}
  - {id: L3, level: 3, all: [{attr: population, op: ">=", value: 50000}]}
  - id: L4
    level: 4
    all:
      - {attr: n_dea, op: ">=", value: 1}
      - {attr: n_secondary_schools, op: ">", value: 1}
      - {attr: station_category, op: ">=", value: silver}
  - id: L5
    level: 5
    all:
      - {attr: n_health, op: ">=", value: 1}
      - {attr: n_secondary_schools, op: ">=", value: 1}
      - {attr: station_category, op: ">=", value: bronze}
  - id: L6
    level: 6
    exactly: 2
    of:
      - {name: health, attr: n_health, op: ">=", value: 1}
      - {name: school, attr: n_secondary_schools, op: ">=", value: 1}
      - {name: station, attr: station_category, op: ">=", value: bronze}
```

- [ ] **Step 2: Write the failing tests `tests/test_levels.py`**

```python
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from builders import make_inputs, scenario
from maps_sll.engine import run
from maps_sll.levels import LevelsError, Rule, RuleSet, assign_levels, load_rules
from maps_sll.output import units_table

RULES = load_rules(Path(__file__).parents[1] / "maps" / "levels" / "maps-rules.yaml")
NONE = {"n_health": 0, "n_dea": 0, "n_secondary_schools": 0, "station_category": None}
ALL = {"n_health": 2, "n_dea": 1, "n_secondary_schools": 3, "station_category": "gold"}


def levels(rows, rules=RULES):
    df = pd.DataFrame([{"id": k, **v} for k, v in rows.items()])
    return assign_levels(df, rules).set_index("id")


def test_C2_population_boundaries_fall_in_the_upper_class():
    out = levels({
        "a": {"population": 250000, **NONE}, "b": {"population": 249999, **NONE},
        "c": {"population": 100000, **NONE}, "d": {"population": 50000, **NONE},
        "e": {"population": 49999, **NONE},
    })
    assert out.level.tolist()[:4] == [1, 2, 2, 3] and pd.isna(out.level["e"])


def test_C2_sixty_thousand_with_all_services_is_level_3():
    assert levels({"a": {"population": 60000, **ALL}}).level["a"] == 3


def test_C5_dea_two_schools_silver_is_level_4():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 2,
           "station_category": "silver"}
    assert levels({"a": row}).level["a"] == 4


def test_C5_dea_two_schools_bronze_is_level_5():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 2,
           "station_category": "bronze"}
    assert levels({"a": row}).level["a"] == 5


def test_C5_dea_one_school_silver_is_level_5():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 1,
           "station_category": "silver"}
    assert levels({"a": row}).level["a"] == 5


def test_C6_level_6_records_the_missing_service():
    base = {"population": 8000, "n_dea": 0}
    out = levels({
        "nostation": {**base, "n_health": 1, "n_secondary_schools": 1, "station_category": None},
        "nohealth": {**base, "n_health": 0, "n_secondary_schools": 1, "station_category": "bronze"},
        "noschool": {**base, "n_health": 1, "n_secondary_schools": 0, "station_category": "bronze"},
    })
    assert out.level.tolist() == [6, 6, 6]
    assert out.missing.to_dict() == {"nostation": "station", "nohealth": "health",
                                     "noschool": "school"}


def test_C1_every_unit_receives_exactly_one_class():
    rng = np.random.default_rng(1)
    cats = [None, "bronze", "silver", "gold", "platinum"]
    rows = {f"u{i}": {"population": int(rng.integers(100, 400000)),
                      "n_health": int(rng.integers(0, 3)), "n_dea": int(rng.integers(0, 2)),
                      "n_secondary_schools": int(rng.integers(0, 4)),
                      "station_category": cats[int(rng.integers(0, 5))]} for i in range(500)}
    out = levels(rows)
    assert len(out) == 500 and out.index.is_unique
    assert set(out.level.dropna().astype(int)) <= {1, 2, 3, 4, 5, 6}


def test_C3_rule_is_recorded():
    out = levels({"a": {"population": 300000, **NONE}, "b": {"population": 10, **NONE}})
    assert out.rule_id["a"] == "L1" and out.rule_id["b"] is None


def test_C4_rules_are_data():
    changed = RULES.model_copy(deep=True)
    changed.rules[2].all_[0].value = 55000
    row = {"a": {"population": 52000, **NONE}}
    assert levels(row).level["a"] == 3 and pd.isna(levels(row, changed).level["a"])


def test_I5_new_dimension_without_engine_changes():
    rules = RuleSet.model_validate({"rules": [
        {"id": "C1", "level": 1, "all": [{"attr": "n_cinemas", "op": ">=", "value": 3}]},
    ]})
    lv = levels({"a": {"n_cinemas": 5}, "u": {"n_cinemas": 0}}, rules)
    units = [("a", int(lv.level["a"]), 1000), ("u", None, 10)]
    r = run(scenario(levels=[1], phase2_pairs={}, phase4_levels=[]),
            make_inputs(units, times={("u", "a"): 5}))
    assert units_table(r).set_index("id").system_id["u"] == "a"


def test_unknown_attribute_is_an_error():
    rules = RuleSet.model_validate({"rules": [
        {"id": "X", "level": 1, "all": [{"attr": "nope", "op": ">=", "value": 1}]}]})
    with pytest.raises(LevelsError, match="nope"):
        levels({"a": {"population": 1}}, rules)


def test_rule_needs_exactly_one_form():
    with pytest.raises(ValueError):
        Rule.model_validate({"id": "X", "level": 1})


def test_R5_levels_run_writes_its_own_manifest(tmp_path):
    from maps_sll.levels import assign_levels_file
    import json
    attrs = tmp_path / "attrs.csv"
    pd.DataFrame([{"id": "a", "population": 300000, **NONE},
                  {"id": "b", "population": 10, **NONE}]).to_csv(attrs, index=False)
    rules = Path(__file__).parents[1] / "maps" / "levels" / "maps-rules.yaml"
    out = tmp_path / "levels.csv"
    assign_levels_file(rules, attrs, out)
    m = json.loads((tmp_path / "levels.csv.manifest.json").read_text(encoding="utf-8"))
    assert m["step"] == "levels"
    assert m["rules"]["fingerprint"].startswith("sha256:")
    assert m["attributes"]["fingerprint"].startswith("sha256:")
    assert m["counts"] == {"units": 2, "by_level": {"1": 1}, "without_level": 1,
                           "by_rule": {"L1": 1}}
```

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_levels.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'maps_sll.levels'`

- [ ] **Step 4: Write `src/maps_sll/levels.py`**

```python
"""Phase 1: level calculation from unit attributes, rules as data (criteria C1-C6)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

OPS = {
    ">=": np.greater_equal, ">": np.greater, "<=": np.less_equal,
    "<": np.less, "==": np.equal, "!=": np.not_equal,
}


class LevelsError(ValueError):
    pass


class Predicate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attr: str
    op: Literal[">=", ">", "<=", "<", "==", "!="]
    value: float | str
    name: str | None = None

    @property
    def label(self) -> str:
        return self.name or self.attr


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str
    level: int
    all_: list[Predicate] | None = Field(default=None, alias="all")
    exactly: int | None = None
    of: list[Predicate] | None = None

    @model_validator(mode="after")
    def _one_form(self) -> "Rule":
        has_all = self.all_ is not None
        has_k = self.exactly is not None and self.of is not None
        if has_all == has_k:
            raise ValueError(f"rule {self.id}: use either 'all' or 'exactly' + 'of'")
        return self


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[Rule]
    ordinal_attributes: dict[str, list[str]] = {}

    @model_validator(mode="after")
    def _unique_ids(self) -> "RuleSet":
        ids = [r.id for r in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError("rule ids must be unique")
        return self


def load_rules(path: str | Path) -> RuleSet:
    return RuleSet.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def _evaluate(df: pd.DataFrame, pred: Predicate, ordinals: dict[str, list[str]]) -> np.ndarray:
    if pred.attr not in df.columns:
        raise LevelsError(f"attribute {pred.attr!r} is not in the input table")
    col = df[pred.attr]
    if pred.attr in ordinals:
        scale = {v.lower(): i for i, v in enumerate(ordinals[pred.attr])}
        left = col.map(lambda v: scale.get(str(v).lower(), -1) if pd.notna(v) else -1)
        left = left.to_numpy(dtype=float)
        key = str(pred.value).lower()
        if key not in scale:
            raise LevelsError(f"{pred.value!r} is not on the scale of {pred.attr}")
        right = float(scale[key])
        valid = left >= 0
    else:
        left = pd.to_numeric(col, errors="coerce").to_numpy(dtype=float)
        right = float(pred.value)
        valid = ~np.isnan(left)
    return OPS[pred.op](left, right) & valid


def assign_levels(attrs: pd.DataFrame, rules: RuleSet) -> pd.DataFrame:
    """One row per unit: level (or NA), the rule that assigned it, the missing services."""
    n = len(attrs)
    level = pd.array([pd.NA] * n, dtype="Int64")
    rule_id = np.full(n, None, dtype=object)
    missing = np.full(n, None, dtype=object)
    done = np.zeros(n, dtype=bool)
    for rule in rules.rules:
        if rule.all_ is not None:
            hit = np.logical_and.reduce([_evaluate(attrs, p, rules.ordinal_attributes)
                                         for p in rule.all_])
            labels = None
        else:
            evals = [_evaluate(attrs, p, rules.ordinal_attributes) for p in rule.of]
            hit = np.sum(evals, axis=0) == rule.exactly
            labels = [",".join(p.label for p, e in zip(rule.of, evals) if not e[i])
                      for i in range(n)]
        sel = hit & ~done
        level[sel] = rule.level
        rule_id[sel] = rule.id
        if labels is not None:
            for i in np.flatnonzero(sel):
                missing[i] = labels[i]
        done |= sel
    return pd.DataFrame({"id": attrs["id"].astype(str).to_numpy(), "level": level,
                         "rule_id": rule_id, "missing": missing})


def assign_levels_file(rules_path, attributes_path, out_path) -> pd.DataFrame:
    """Run phase 1 from files and write, next to the output, `<out>.manifest.json`:
    the levels are a product of their own, calibrated separately from the aggregation."""
    src, out, rules_file = Path(attributes_path), Path(out_path), Path(rules_path)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    attrs = (pd.read_parquet(src) if src.suffix == ".parquet"
             else pd.read_csv(src, dtype={"id": str}))
    rules = load_rules(rules_file)
    result = assign_levels(attrs, rules)
    if out.suffix == ".parquet":
        result.to_parquet(out, index=False)
    else:
        result.to_csv(out, index=False)
    manifest = {
        "package": "maps-sll",
        "package_version": __version__,
        "step": "levels",
        "rules": {"path": str(rules_file), "fingerprint": "sha256:" + _sha256(rules_file),
                  "content": rules.model_dump(mode="json", by_alias=True)},
        "attributes": {"path": str(src), "fingerprint": "sha256:" + _sha256(src)},
        "counts": {
            "units": int(len(result)),
            "by_level": {str(k): int(v) for k, v in
                         result.level.value_counts().sort_index().items()},
            "without_level": int(result.level.isna().sum()),
            "by_rule": {str(k): int(v) for k, v in
                        result.rule_id.value_counts().sort_index().items()},
        },
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    out.with_name(out.name + ".manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
```

Add at the top of `levels.py`, with the other imports:

```python
import hashlib
import json
from datetime import UTC, datetime

from . import __version__
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/pytest tests/test_levels.py`
Expected: `13 passed`

- [ ] **Step 6: Run the whole suite and ruff, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check src tests`
Expected: all pass.

```bash
git add -A && git commit -m "feat: phase 1 rule engine and MAPS level rules"
```

---

### Task 11: MAPS data preparation

The GSSI zip of 16/10/2026 is unpacked in a local directory, outside the repository. These scripts are run once by hand; they are not unit-tested (the national checks of Task 13 validate their output).

**Files:**
- Create: `maps/prepare/convert.py`, `maps/prepare/fusions_draft.py`, `maps/prepare/reconduct.py`, `maps/prepare/build_units.py`, `maps/reference/fusions-2021-2025.csv`, `maps/README.md`

- [ ] **Step 1: Link the GSSI data**

```bash
mkdir -p maps/data && ln -s /path/to/gssi-data maps/data/gssi
```

- [ ] **Step 2: Write `maps/prepare/convert.py`**

```python
"""Convert the GSSI Stata files (zip of 16/10/2026) to Parquet.

    python maps/prepare/convert.py maps/data/gssi maps/data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def code(s: pd.Series) -> pd.Series:
    return s.astype("int64").astype(str).str.zfill(6)


def convert_times(src: Path, dst: Path, chunksize: int = 5_000_000) -> int:
    """distanze_2021.dta -> origin, destination (2021 ISTAT codes, int), minutes (ttp_tot,
    free-flow, decision D17). tep_tot and km_tot are dropped."""
    schema = pa.schema([("origin", pa.int32()), ("destination", pa.int32()),
                        ("minutes", pa.int16())])
    n = 0
    with pq.ParquetWriter(dst, schema) as writer, pd.read_stata(
        src, columns=["cod_istat_or", "cod_istat_dest", "ttp_tot"], chunksize=chunksize,
        convert_categoricals=False,
    ) as reader:
        for chunk in reader:
            table = pa.table({
                "origin": chunk["cod_istat_or"].astype("int32"),
                "destination": chunk["cod_istat_dest"].astype("int32"),
                "minutes": chunk["ttp_tot"].astype("int16"),
            }, schema=schema)
            writer.write_table(table)
            n += len(chunk)
    return n


def convert_contiguity(src: Path, dst: Path) -> int:
    df = pd.read_stata(src)
    out = pd.DataFrame({
        "origin": code(df["PRO_COM_N"]),
        "neighbour": code(df["PRO_COM_A"]),
        "origin_name": df["COMUNE"].astype(str),
        "shared_length": df["lunghezza_km"].astype("float64"),
        "origin_perimeter": df["lunghezza_km_tot"].astype("float64"),
    })
    out.to_parquet(dst, index=False)
    return len(out)


def convert_levels(src: Path, dst: Path) -> int:
    df = pd.read_stata(src)
    out = pd.DataFrame({
        "id": code(df["PRO_COM"]),
        "name": df["Comune"].astype(str),
        "level": df["centralità"].astype("Int64"),
        "gssi_tier": df["tutto"].astype(str),
        "population": df["Pop_1125"].astype("int64"),
        "n_health": df["NUM_OSPEDALI"],
        "n_dea": df["NUM_DEA"],
        "pnrr_m6": df["PNRR_Missione6"],
        "n_school_types": df["conta_tipi_scuoleSUP"],
        "snai_school_index": df["IND_scuoleSUP_snai"],
        "station_category": df["Stazioni_max_METALLI"].astype(str).str.strip().str.lower()
        .replace({"": None, "nan": None}),
    })
    out.to_parquet(dst, index=False)
    return len(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    a = ap.parse_args()
    a.dst.mkdir(parents=True, exist_ok=True)
    print("contiguity", convert_contiguity(a.src / "comuni_matrice_contiguità.dta",
                                           a.dst / "contiguity-2025.parquet"))
    print("levels", convert_levels(a.src / "centralità.dta", a.dst / "levels-gssi.parquet"))
    print("times", convert_times(a.src / "distanze_2021.dta", a.dst / "times-2021.parquet"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the conversion**

Run: `.venv/bin/python -I maps/prepare/convert.py maps/data/gssi maps/data`
Expected: `contiguity 46442`, `levels 1259`, `times` followed by the number of pairs (about 62 million). If a column name differs from the ones above, print `pd.read_stata(path, iterator=True).variable_labels()` and fix the mapping.

- [ ] **Step 4: Export the 2025 population of all municipalities from the Datastore**

The source is the ISTAT resident population on 1 January 2025 (demo.istat.it, POS), also published in the MAPS Datastore. Write `id` (ISTAT code valid on 2025-01-01), `name` and `population` to `maps/data/population-2025.csv`. Expected: 7,896 municipalities. Write the CSV so that names such as "None" (municipality 001168) are not read back as missing values.

- [ ] **Step 5: Write `maps/prepare/build_units.py`**

```python
"""Units table for the national run: 2025 population of every municipality + GSSI levels.

    python maps/prepare/build_units.py maps/data/population-2025.csv \
        maps/data/levels-gssi.parquet maps/data/units-2025.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def build_units(population: Path, levels: Path) -> pd.DataFrame:
    pop = pd.read_csv(population, dtype={"id": str})
    pop["id"] = pop["id"].str.zfill(6)
    lv = pd.read_parquet(levels, columns=["id", "level"])
    absent = sorted(set(lv.id) - set(pop.id))
    if absent:
        raise SystemExit(f"GSSI centralities absent from the 2025 population: {absent}")
    units = pop.merge(lv, on="id", how="left").rename(columns={"population": "weight"})
    units["level"] = units["level"].astype("Int64")
    return units[["id", "name", "level", "weight"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("population", type=Path)
    ap.add_argument("levels", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    units = build_units(a.population, a.levels)
    units.to_parquet(a.out, index=False)
    print(len(units), "units,", int(units.level.notna().sum()), "centralities")


if __name__ == "__main__":
    main()
```

Run: `.venv/bin/python -I maps/prepare/build_units.py maps/data/population-2025.csv maps/data/levels-gssi.parquet maps/data/units-2025.parquet`
Expected: about `7896 units, 1259 centralities`.

- [ ] **Step 6: Write `maps/prepare/fusions_draft.py`**

```python
"""List the codes that the 2021 matrix and the 2025 units do not share.

Writes a draft of maps/reference/fusions-2021-2025.csv to complete by hand.

    python maps/prepare/fusions_draft.py maps/data/times-2021.parquet \
        maps/data/units-2025.parquet maps/reference/fusions-2021-2025.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("times", type=Path)
    ap.add_argument("units", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    con = duckdb.connect()
    old = con.execute(
        f"""SELECT DISTINCT lpad(CAST(origin AS VARCHAR), 6, '0') AS code
            FROM read_parquet('{a.times}')
            EXCEPT SELECT id FROM read_parquet('{a.units}') ORDER BY 1"""
    ).fetchall()
    new = con.execute(
        f"""SELECT id FROM read_parquet('{a.units}')
            EXCEPT SELECT DISTINCT lpad(CAST(origin AS VARCHAR), 6, '0')
            FROM read_parquet('{a.times}') ORDER BY 1"""
    ).fetchall()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        f.write("code_2021,code_2025,is_seat,note\n")
        for (c,) in old:
            f.write(f"{c},,,\n")
    print(f"{len(old)} codes of 2021 without a 2025 match -> {a.out}")
    print(f"{len(new)} codes of 2025 without times: {[c for (c,) in new]}")


if __name__ == "__main__":
    main()
```

Run: `.venv/bin/python -I maps/prepare/fusions_draft.py maps/data/times-2021.parquet maps/data/units-2025.parquet maps/reference/fusions-2021-2025.csv`
Expected: a few dozen 2021 codes (municipalities merged between 2021 and 2025), and among the 2025 codes without times the new merged municipalities and Misiliscemi.

- [ ] **Step 7: Complete `maps/reference/fusions-2021-2025.csv` by hand**

For every 2021 code: `code_2025` is the 2025 municipality it merged into; `is_seat` is `true` for the municipality that hosts the town hall of the new municipality (decision D10), `false` for the others; `note` cites the merger (law and date). Source: the ISTAT list of administrative changes (variazioni amministrative). Every merger needs exactly one `true`. This step is manual: show the completed table to the user before going on.

- [ ] **Step 8: Write `maps/prepare/reconduct.py`**

```python
"""Reconduct the 2021 travel-time matrix to the 2025 municipalities (decision D10, R6).

    python maps/prepare/reconduct.py maps/data/times-2021.parquet \
        maps/reference/fusions-2021-2025.csv maps/data/units-2025.parquet maps/data
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

MAPPED = """
SELECT coalesce(fo.code_2025, t.o) AS origin,
       coalesce(fd.code_2025, t.d) AS destination,
       t.minutes
FROM (SELECT lpad(CAST(origin AS VARCHAR), 6, '0') AS o,
             lpad(CAST(destination AS VARCHAR), 6, '0') AS d, minutes
      FROM read_parquet('{times}')) t
LEFT JOIN fus fo ON fo.code_2021 = t.o
LEFT JOIN fus fd ON fd.code_2021 = t.d
WHERE coalesce(fo.is_seat, true) AND coalesce(fd.is_seat, true)
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("times", type=Path)
    ap.add_argument("fusions", type=Path)
    ap.add_argument("units", type=Path)
    ap.add_argument("out_dir", type=Path)
    a = ap.parse_args()
    con = duckdb.connect()
    con.execute(
        f"""CREATE TABLE fus AS SELECT code_2021, code_2025,
            lower(is_seat) IN ('true', '1', 'yes') AS is_seat, note
            FROM read_csv('{a.fusions}', all_varchar = true)"""
    )
    incomplete = con.execute(
        "SELECT code_2021 FROM fus WHERE code_2025 IS NULL OR code_2025 = ''"
    ).fetchall()
    if incomplete:
        raise SystemExit(f"fusions table incomplete: {[c for (c,) in incomplete]}")
    seats = con.execute(
        "SELECT code_2025, count(*) FILTER (WHERE is_seat) AS n FROM fus GROUP BY 1 HAVING n <> 1"
    ).fetchall()
    if seats:
        raise SystemExit(f"every merger needs exactly one seat: {seats}")
    con.execute(f"CREATE TABLE units AS SELECT id FROM read_parquet('{a.units}')")
    mapped = MAPPED.format(times=a.times)
    outside = con.execute(
        f"SELECT DISTINCT origin FROM ({mapped}) WHERE origin NOT IN (SELECT id FROM units)"
    ).fetchall()
    if outside:
        raise SystemExit(f"2021 codes neither in the 2025 units nor in the fusions table: "
                         f"{[c for (c,) in outside][:20]}")
    dup = con.execute(
        f"SELECT count(*) FROM (SELECT origin, destination FROM ({mapped}) "
        "GROUP BY 1, 2 HAVING count(*) > 1)"
    ).fetchone()[0]
    if dup:
        raise SystemExit(f"{dup} duplicated pairs after the reconduction")
    out = a.out_dir / "times-2025.parquet"
    con.execute(f"COPY ({mapped} ORDER BY 1, 2) TO '{out}' (FORMAT parquet)")
    con.execute(f"COPY (SELECT code_2021, code_2025, is_seat AS kept, note FROM fus ORDER BY 1) "
                f"TO '{a.out_dir / 'reconducted.csv'}' (HEADER)")
    without = [c for (c,) in con.execute(
        f"SELECT id FROM units EXCEPT SELECT DISTINCT origin FROM read_parquet('{out}') ORDER BY 1"
    ).fetchall()]
    rows = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    summary = {
        "travel_time_reconduction": {
            "rule": "decision D10: the municipality hosting the town hall survives",
            "reconducted": [dict(zip(("code_2021", "code_2025", "kept"), r)) for r in
                            con.execute("SELECT code_2021, code_2025, is_seat FROM fus "
                                        "ORDER BY 1").fetchall()],
            "units_without_times": without,
            "pairs": rows,
        }
    }
    (a.out_dir / "reconduction.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{rows} pairs; units without times: {without}")


if __name__ == "__main__":
    main()
```

Run: `.venv/bin/python -I maps/prepare/reconduct.py maps/data/times-2021.parquet maps/reference/fusions-2021-2025.csv maps/data/units-2025.parquet maps/data`
Expected: no `SystemExit`; among the units without times there is Misiliscemi (`081024`).

- [ ] **Step 9: Write `maps/README.md`**

```markdown
# maps/ — application to the Italian municipalities (MAPS)

Not part of the installable package. Run once, in order:

1. `maps/prepare/convert.py` — GSSI `.dta` (zip of 16/10/2026) → Parquet in `maps/data/`
2. population 2025 from the Datastore → `maps/data/population-2025.csv` (query in the
   implementation plan, Task 11, Step 4)
3. `maps/prepare/build_units.py` — units = population + GSSI levels
4. `maps/prepare/fusions_draft.py`, then complete `maps/reference/fusions-2021-2025.csv` by hand
5. `maps/prepare/reconduct.py` — 2021 matrix → 2025 codes (decision D10)
6. `maps-sll run maps/scenarios/maps-2025.yaml --out output/maps-2025 --manifest-extra maps/data/reconduction.json`
7. `python maps/checks.py output/maps-2025 maps/data/units-2025.parquet`

`maps/data/` is not versioned. The GSSI data (Stata routine and input files of 16/10/2026) are provided by GSSI and are not redistributed here.
```

- [ ] **Step 10: Commit (the fusions table only once complete)**

```bash
git add maps/prepare maps/reference maps/README.md && git commit -m "feat(maps): data preparation for the national run"
```

---

### Task 12: MAPS scenario and phase-1 comparison with GSSI

**Files:**
- Create: `maps/scenarios/maps-2025.yaml`, `maps/levels_gssi.py`

- [ ] **Step 1: Write `maps/scenarios/maps-2025.yaml`**

```yaml
# MAPS scenario, reference year 2025 (D3.2.1 appendix A1; decisions D5, D13, D14, D15, D17).
name: maps-2025
reference_year: 2025
levels: [1, 2, 3, 4, 5, 6]
phase2_pairs:
  2: [1]
  3: [1]
  4: [1, 2]
  5: [1, 2, 3]
  6: [1, 2, 3]
phase4_levels: [4, 5, 6]
contiguity:
  min_shared_share: 0.0309
  max_minutes: 20
distant_minutes: 60
id_order: numeric
max_chain_length: 16
inputs:
  units: ../data/units-2025.parquet
  contiguity: ../data/contiguity-2025.parquet
  travel_times:
    path: ../data/times-2025.parquet
    description: >-
      ISTAT travel-time matrix on TomTom graph, free-flow minutes (ttp_tot), 2021 boundaries
      reconducted to 2025 (decision D10); GSSI zip of 16/10/2026
```

- [ ] **Step 2: Write `maps/levels_gssi.py`**

```python
"""Phase 1 with the MAPS rules on the 1,259 GSSI centralities, compared with GSSI levels.

Approximation: GSSI has no count of upper-secondary schools, only the number of school types
(conta_tipi_scuoleSUP), used here as n_secondary_schools. Differences are expected where the
GSSI definitions (PNRR Mission 6, SNAI index) differ from decision D16.

    python maps/levels_gssi.py maps/data/levels-gssi.parquet maps/levels/maps-rules.yaml out/
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from maps_sll.levels import assign_levels, load_rules


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("levels", type=Path)
    ap.add_argument("rules", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    g = pd.read_parquet(a.levels)
    attrs = g.rename(columns={"n_school_types": "n_secondary_schools"})
    ours = assign_levels(attrs, load_rules(a.rules)).rename(columns={"level": "level_ours"})
    cmp = g[["id", "name", "level", "gssi_tier", "population", "n_health", "n_dea", "pnrr_m6",
             "n_school_types", "snai_school_index", "station_category"]].merge(ours, on="id")
    cmp = cmp.rename(columns={"level": "level_gssi"})
    a.out.mkdir(parents=True, exist_ok=True)
    cmp.to_csv(a.out / "levels-gssi-comparison.csv", index=False)
    table = pd.crosstab(cmp.level_gssi, cmp.level_ours.astype("string").fillna("none"))
    (a.out / "levels-gssi-crosstab.md").write_text(table.to_markdown(), encoding="utf-8")
    same = int((cmp.level_gssi == cmp.level_ours).sum())
    print(f"same level: {same}/{len(cmp)}")
    print(table)


if __name__ == "__main__":
    main()
```

(`DataFrame.to_markdown` needs `tabulate`: add `"tabulate>=0.9"` to the `maps` extra in `pyproject.toml` and reinstall with `uv pip install -e '.[dev,maps]'`.)

- [ ] **Step 3: Run the comparison**

Run: `.venv/bin/python -I maps/levels_gssi.py maps/data/levels-gssi.parquet maps/levels/maps-rules.yaml output/levels-gssi`
Expected: a crosstab GSSI × ours. Levels 1–3 depend only on population and must coincide exactly; differences on levels 4–6 are the material for the D16 question to GSSI. Report the counts to the user.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat(maps): MAPS scenario and phase-1 comparison with GSSI levels"
```

---

### Task 13: National run and checks

**Files:**
- Create: `maps/checks.py`

- [ ] **Step 1: Write `maps/checks.py`**

```python
"""Checks on a national run (criteria C1, S1, S5, S8, O2, O3, R1, R6, P1, P2).

    python maps/checks.py output/maps-2025 maps/data/units-2025.parquet \
        [--reference-run output/maps-2025-bis]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

P1_LIMIT_SECONDS = 600  # decision D20


def check(run_dir: Path, units_input: Path, reference: Path | None) -> dict:
    units = pd.read_parquet(run_dir / "units.parquet")
    systems = pd.read_parquet(run_dir / "systems.parquet")
    unassigned = pd.read_parquet(run_dir / "unassigned.parquet")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    weight = pd.read_parquet(units_input, columns=["id", "weight"]).set_index("id").weight
    levels = set(manifest["scenario"]["levels"])
    timings = manifest["timings_seconds"]
    total = sum(v for k, v in timings.items() if k != "core")
    heads = units.set_index("id").loc[systems.system_id]
    recomputed = units.assign(w=units.id.map(weight)).groupby("system_id").w.sum()
    res = {
        "C1": bool(units.level.dropna().astype(int).isin(levels).all()),
        "S1": bool(units[units.level.isna()].direct_step_id.notna().all()),
        "S5": {"n_distant": int(units.distant.sum()),
               "distant_all_assigned": bool(units[units.distant].system_id.notna().all())},
        "S8": bool((heads.role == "main_centre").all()),
        "O2": bool(units.id.is_unique),
        "O3": bool(np.allclose(systems.set_index("system_id").total_weight.sort_index(),
                               recomputed.sort_index())),
        "R6": {"units_without_times": unassigned.id.tolist(),
               "reconducted": len(manifest.get("extra", {}).get("travel_time_reconduction", {})
                                  .get("reconducted", []))},
        "P1": {"total_seconds": round(total, 2), "limit": P1_LIMIT_SECONDS,
               "ok": total <= P1_LIMIT_SECONDS},
        "P2": {k: round(v, 3) for k, v in timings.items()},
    }
    if reference is not None:  # R1: same scenario, same data, identical tables
        res["R1"] = all(
            pd.read_parquet(run_dir / f"{t}.parquet").equals(
                pd.read_parquet(reference / f"{t}.parquet"))
            for t in ("units", "systems", "distant", "unassigned")
        )
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("units_input", type=Path)
    ap.add_argument("--reference-run", type=Path)
    a = ap.parse_args()
    res = check(a.run_dir, a.units_input, a.reference_run)
    (a.run_dir / "checks.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
```

O3 is recomputed independently here: the weight of every system against the sum of the weights of its members, read from the input units table.

- [ ] **Step 2: National run, twice (R1), and a variant at 30 minutes (S6, P3)**

```bash
.venv/bin/maps-sll run maps/scenarios/maps-2025.yaml --out output/maps-2025 --manifest-extra maps/data/reconduction.json
.venv/bin/maps-sll run maps/scenarios/maps-2025.yaml --out output/maps-2025-bis --manifest-extra maps/data/reconduction.json
sed 's/^distant_minutes: 60/distant_minutes: 30/; s/^name: maps-2025/name: maps-2025-d30/' maps/scenarios/maps-2025.yaml > maps/scenarios/maps-2025-d30.yaml
.venv/bin/maps-sll run maps/scenarios/maps-2025-d30.yaml --out output/maps-2025-d30 --manifest-extra maps/data/reconduction.json
.venv/bin/python -I maps/checks.py output/maps-2025 maps/data/units-2025.parquet --reference-run output/maps-2025-bis
```

Expected: every boolean `true`; `P1.ok` true; `R6.units_without_times` contains `081024` (Misiliscemi). If `build_problem` raises an `InputError` on contiguity ids, the contiguity file uses codes that are not 2025 codes: stop and report to the user.

- [ ] **Step 3: Compare the 60- and 30-minute runs (S6) and read P3**

```bash
.venv/bin/python -I -c "
import pandas as pd, json
a = pd.read_parquet('output/maps-2025/units.parquet'); b = pd.read_parquet('output/maps-2025-d30/units.parquet')
print('S6 same assignment:', a.system_id.equals(b.system_id), 'distant 60/30:', int(a.distant.sum()), int(b.distant.sum()))
for d in ('output/maps-2025', 'output/maps-2025-d30'):
    t = json.load(open(d + '/manifest.json'))['timings_seconds']; print(d, {k: round(v, 2) for k, v in t.items()})
"
```

Expected: `S6 same assignment: True`; P3 is satisfied when the second run's `read_inputs` + `build_problem` read the same Parquet matrix without recomputing it (no step of the run recomputes times or borders).

- [ ] **Step 4: Commit**

```bash
git add maps/checks.py maps/scenarios/maps-2025-d30.yaml && git commit -m "feat(maps): national-run checks"
```

---

### Task 14: Traceability table for the D3.2.1

**Files:**
- Create: `tools/criteria.yaml`, `tools/traceability.py`

- [ ] **Step 1: Write `tools/criteria.yaml`**

```yaml
# Acceptance criteria of the D3.2.1 and where their evidence comes from.
# evidence: tests (pytest names starting with test_<ID>_), national (maps/checks.py),
# inspection (manual reading of output/manifest), external (depends on something outside).
R1: {evidence: [tests, national]}
R2: {evidence: [inspection], note: "the CLI reads only the scenario file"}
R3: {evidence: [external], note: "run on a second machine"}
R4: {evidence: [tests]}
R5: {evidence: [tests]}
R6: {evidence: [tests, national]}
C1: {evidence: [tests, national]}
C2: {evidence: [tests]}
C3: {evidence: [tests]}
C4: {evidence: [tests]}
C5: {evidence: [tests]}
C6: {evidence: [tests]}
I1: {evidence: [tests]}
I2: {evidence: [tests], note: "database part depends on decision D9"}
I3: {evidence: [tests]}
I4: {evidence: [tests]}
I5: {evidence: [tests], note: "database part depends on decision D9"}
I6: {evidence: [tests]}
I7: {evidence: [tests]}
A1: {evidence: [tests]}
A2: {evidence: [tests]}
A3: {evidence: [tests]}
A4: {evidence: [tests]}
A5: {evidence: [tests]}
A6: {evidence: [tests]}
A7: {evidence: [tests]}
A8: {evidence: [tests]}
A9: {evidence: [tests]}
A10: {evidence: [tests]}
A11: {evidence: [tests]}
A12: {evidence: [tests]}
S1: {evidence: [national]}
S2: {evidence: [tests]}
S3: {evidence: [tests]}
S4: {evidence: [tests]}
S5: {evidence: [tests, national]}
S6: {evidence: [tests, national]}
S7: {evidence: [tests]}
S8: {evidence: [tests, national]}
O1: {evidence: [external], note: "schema of the MAPS table of the attractors, decision D9"}
O1b: {evidence: [tests]}
O2: {evidence: [tests, national]}
O3: {evidence: [tests, national]}
O5: {evidence: [tests]}
O6: {evidence: [tests]}
P1: {evidence: [national]}
P2: {evidence: [tests, national]}
P3: {evidence: [national]}
```

- [ ] **Step 2: Write `tools/traceability.py`**

```python
"""Criterion -> evidence -> outcome table for the "Esito" section of the D3.2.1.

    pytest --junitxml=output/junit.xml
    python tools/traceability.py output/junit.xml output/maps-2025/checks.json > output/esito.md
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

TEST_IDS = re.compile(r"^test_((?:[A-Z]\d+b?_)+)")


def from_junit(path: Path) -> dict[str, list[tuple[str, bool]]]:
    out: dict[str, list[tuple[str, bool]]] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        m = TEST_IDS.match(case.get("name", ""))
        if not m:
            continue
        failed = any(child.tag in ("failure", "error") for child in case)
        for cid in m.group(1).strip("_").split("_"):  # test_O2_O3_... covers O2 and O3
            out.setdefault(cid, []).append((case.get("name"), not failed))
    return out


def national_ok(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return all(national_ok(v) for k, v in value.items() if isinstance(v, bool) or k == "ok")
    return True


def main(junit: str, checks: str | None = None) -> None:
    criteria = yaml.safe_load((Path(__file__).parent / "criteria.yaml").read_text())
    tests = from_junit(Path(junit))
    national = json.loads(Path(checks).read_text()) if checks else {}
    print("| Criterion | Evidence | Outcome |")
    print("|---|---|---|")
    for cid, spec in criteria.items():
        evidence, outcomes = [], []
        if "tests" in spec["evidence"]:
            cases = tests.get(cid, [])
            evidence.append(f"{len(cases)} tests" if cases else "no test")
            outcomes.append(bool(cases) and all(ok for _, ok in cases))
        if "national" in spec["evidence"]:
            if cid in national:
                evidence.append("national run")
                outcomes.append(national_ok(national[cid]))
            else:
                evidence.append("national run missing")
                outcomes.append(None)
        if set(spec["evidence"]) & {"inspection", "external"}:
            evidence.append(spec.get("note", spec["evidence"][0]))
            outcomes.append(None)
        if any(o is False for o in outcomes):
            outcome = "not satisfied"
        elif outcomes and all(o is True for o in outcomes):
            outcome = "satisfied"
        else:
            outcome = "not verifiable" + (f" ({spec['note']})" if spec.get("note") else "")
        print(f"| {cid} | {'; '.join(evidence)} | {outcome} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
```

- [ ] **Step 3: Produce the table**

```bash
.venv/bin/pytest --junitxml=output/junit.xml
.venv/bin/python -I tools/traceability.py output/junit.xml output/maps-2025/checks.json > output/esito.md
cat output/esito.md
```

Expected: one row per criterion. Every criterion with `tests` evidence has at least one test; R3, O1 and the parts of I2/I5 that depend on decision D9 are "not verifiable" with their reason. A "no test" row is a gap in this plan: add the test before going on.

- [ ] **Step 4: Commit**

```bash
git add tools && git commit -m "feat: traceability table criteria -> tests -> outcome"
```

- [ ] **Step 5: Update `STATUS.md`**

Close the line "implementation plan from the design", add one line per open outcome of `output/esito.md` (criterion, reason), and commit:

```bash
git add STATUS.md && git commit -m "docs: STATUS after the first national run"
```
