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
        if "inspection" in spec["evidence"]:
            evidence.append(spec.get("note", "inspection"))
            # a reading counts only once it is dated in criteria.yaml
            outcomes.append(True if spec.get("verified") else None)
        if "external" in spec["evidence"]:
            evidence.append(spec.get("note", "external"))
            outcomes.append(None)
        if any(o is False for o in outcomes):
            outcome = "not satisfied"
        elif outcomes and all(o is True for o in outcomes):
            outcome = "satisfied" + (f" (code reading, {spec['verified']})"
                                     if spec.get("verified") else "")
        else:
            outcome = "not verifiable" + (f" ({spec['note']})" if spec.get("note") else "")
        print(f"| {cid} | {'; '.join(evidence)} | {outcome} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
