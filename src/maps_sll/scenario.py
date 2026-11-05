"""Scenario: the only source of parameters of an execution (criterion R2)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, StrictInt, model_validator


class Contiguity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_shared_share: float  # relevant when the share is strictly greater
    max_minutes: float  # relevant when the time is strictly lower

    @model_validator(mode="after")
    def _check(self) -> Contiguity:
        for name in ("min_shared_share", "max_minutes"):
            v = getattr(self, name)
            if not v >= 0:  # also rejects NaN
                raise ValueError(f"contiguity.{name} must be a number >= 0")
        return self


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
    max_chain_length: StrictInt = 16
    inputs: InputPaths | None = None

    @model_validator(mode="after")
    def _check(self) -> Scenario:
        if not self.levels:
            raise ValueError("levels must not be empty")
        if not self.distant_minutes >= 0:
            raise ValueError("distant_minutes must be a number >= 0")
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
        if self.id_order_list is not None:
            if self.id_order != "explicit":
                raise ValueError("id_order_list is only allowed when id_order is 'explicit'")
            if len(set(self.id_order_list)) != len(self.id_order_list):
                raise ValueError("id_order_list must not contain duplicates")
        if self.max_chain_length < 1:
            raise ValueError("max_chain_length must be at least 1")
        return self

    def strength(self, level: int) -> int:
        """Position of the level in the scheme: 0 is the strongest."""
        return self.levels.index(level)


def load_scenario(path: str | Path) -> Scenario:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Scenario.model_validate(data)
