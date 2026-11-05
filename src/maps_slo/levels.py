"""Phase 1: level calculation from unit attributes, rules as data (criteria C1-C6)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import __version__
from .manifest import _git_commit

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
    def _one_form(self) -> Rule:
        has_all = self.all_ is not None
        has_k = self.exactly is not None and self.of is not None
        partial_k = (self.exactly is None) != (self.of is None)
        if has_all == has_k or partial_k:
            raise ValueError(f"rule {self.id}: use either 'all' or 'exactly' + 'of', not both")
        if not (self.all_ if has_all else self.of):
            raise ValueError(f"rule {self.id}: the predicate list is empty")
        return self


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[Rule]
    ordinal_attributes: dict[str, list[str]] = {}

    @model_validator(mode="after")
    def _unique_ids(self) -> RuleSet:
        ids = [r.id for r in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError("rule ids must be unique")
        return self


def load_rules(path: str | Path) -> RuleSet:
    return RuleSet.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def _evaluate(df: pd.DataFrame, pred: Predicate,
              ordinals: dict[str, list[str]]) -> tuple[np.ndarray, np.ndarray]:
    """Three-valued predicate: returns (true, unknown) masks; false is neither.

    Numeric attributes: NaN/NA makes the predicate unknown. Ordinal attributes: NA or an
    empty string means *absent* (below the scale), a known value, because "no station" is
    information; a non-empty value that is not on the scale is an error."""
    if pred.attr not in df.columns:
        raise LevelsError(f"attribute {pred.attr!r} is not in the input table")
    col = df[pred.attr]
    if pred.attr in ordinals:
        scale = {v.strip().lower(): i for i, v in enumerate(ordinals[pred.attr])}
        clean = col.map(lambda v: "" if pd.isna(v) else str(v).strip())
        bad = sorted({v for v in clean if v and v.lower() not in scale})
        if bad:
            raise LevelsError(
                f"values of {pred.attr} not on the scale {ordinals[pred.attr]}: {bad}")
        left = clean.map(lambda v: scale[v.lower()] if v else -1).to_numpy(dtype=float)
        key = str(pred.value).strip().lower()
        if key not in scale:
            raise LevelsError(f"{pred.value!r} is not on the scale of {pred.attr}")
        return OPS[pred.op](left, float(scale[key])), np.zeros(len(df), dtype=bool)
    left = pd.to_numeric(col, errors="coerce").to_numpy(dtype=float)
    unknown = np.isnan(left)
    with np.errstate(invalid="ignore"):
        true = OPS[pred.op](left, float(pred.value)) & ~unknown
    return true, unknown


def _rule_state(attrs: pd.DataFrame, rule: Rule, ordinals):
    """(true, unknown, evals) of a rule; false is neither. evals: per-predicate (true, unknown)."""
    preds = rule.all_ if rule.all_ is not None else rule.of
    evals = [_evaluate(attrs, p, ordinals) for p in preds]
    t = np.sum([e[0] for e in evals], axis=0)
    u = np.sum([e[1] for e in evals], axis=0)
    if rule.all_ is not None:
        true = t == len(preds)
        false = (len(preds) - u - t) > 0  # some predicate is certainly false
    else:
        k = rule.exactly
        true = (u == 0) & (t == k)
        false = (t > k) | (t + u < k) | ((u == 0) & (t != k))
    return true, ~true & ~false, evals


def assign_levels(attrs: pd.DataFrame, rules: RuleSet) -> pd.DataFrame:
    """One row per unit: level (or NA), the rule that assigned it, the missing services.

    A NaN/NA in a numeric attribute makes the predicates using it *unknown*. Rules are walked
    in order: the first that is certainly true wins; if a rule that is not certainly false
    (unknown) is met before any true one, the outcome could change with the missing datum, so
    the unit gets level NA, `rule_id` "INCOMPLETE" and `incomplete_attrs` lists the attributes
    that were NA in that rule. For ordinal attributes NA means absent (below the scale)."""
    if "id" not in attrs.columns:
        raise LevelsError("the input table has no 'id' column")
    if pd.api.types.is_float_dtype(attrs["id"].dtype):
        raise LevelsError("float ids: ids must be strings")
    if attrs["id"].isna().any():
        raise LevelsError("unit ids must not be missing")
    dup = attrs["id"].astype(str)
    dup = dup[dup.duplicated()].unique()[:5]
    if len(dup):
        raise LevelsError(f"duplicate unit ids: {list(dup)}")
    n = len(attrs)
    level = pd.array([pd.NA] * n, dtype="Int64")
    rule_id = np.full(n, None, dtype=object)
    missing = np.full(n, None, dtype=object)
    incomplete = np.full(n, None, dtype=object)
    done = np.zeros(n, dtype=bool)
    for rule in rules.rules:
        true, unknown, evals = _rule_state(attrs, rule, rules.ordinal_attributes)
        preds = rule.all_ if rule.all_ is not None else rule.of
        sel = true & ~done
        level[sel] = rule.level
        rule_id[sel] = rule.id
        if rule.of is not None:
            for i in np.flatnonzero(sel):
                missing[i] = ",".join(p.label for p, e in zip(preds, evals) if not e[0][i])
        done |= sel
        inc = unknown & ~done
        for i in np.flatnonzero(inc):
            rule_id[i] = "INCOMPLETE"
            incomplete[i] = ",".join(dict.fromkeys(
                p.attr for p, e in zip(preds, evals) if e[1][i]))
        done |= inc
    return pd.DataFrame({
        "id": attrs["id"].astype(str).to_numpy(), "level": level,
        "rule_id": pd.Series(rule_id, dtype=object), "missing": pd.Series(missing, dtype=object),
        "incomplete_attrs": pd.Series(incomplete, dtype=object),
    })


def _csv_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def assign_levels_file(rules_path, attributes_path, out_path) -> pd.DataFrame:
    """Run phase 1 from files and write, next to the output, `<out>.manifest.json`:
    the levels are a product of their own, calibrated separately from the aggregation."""
    src, out, rules_file = Path(attributes_path), Path(out_path), Path(rules_path)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    attrs = (pd.read_parquet(src) if src.suffix == ".parquet"
             else pd.read_csv(src, dtype={"id": str}, keep_default_na=False,
                              na_values={c: ["", "NA", "NaN", "nan", "None", "null"]
                                         for c in _csv_header(src) if c != "id"}))
    rules = load_rules(rules_file)
    result = assign_levels(attrs, rules)
    if out.suffix == ".parquet":
        result.to_parquet(out, index=False)
    else:
        result.to_csv(out, index=False)
    manifest = {
        "package": "maps-slo",
        "package_version": __version__,
        "git_commit": _git_commit(),
        "step": "levels",
        "rules": {"path": str(rules_file), "fingerprint": "sha256:" + _sha256(rules_file),
                  "content": rules.model_dump(mode="json", by_alias=True)},
        "attributes": {"path": str(src), "fingerprint": "sha256:" + _sha256(src)},
        "counts": {
            "units": len(result),
            "by_level": {str(k): int(v) for k, v in
                         result.level.value_counts().sort_index().items()},
            "without_level": int(result.level.isna().sum()),
            "incomplete": int((result.rule_id == "INCOMPLETE").sum()),
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
