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
    # Metric V10: pairs (previous head, direct claimant). A claimed centrality that already
    # had units pointing to it now points to the claimant, which becomes the head.
    changed_heads: list[tuple[int, int]] = field(default_factory=list)


def phase4(p: Problem, scenario: Scenario, ptr3: np.ndarray) -> Phase4Result:
    """Determinism rules (A1, "Trattamento simultaneo", fixed on 2026-11-05): a claim loser and a claimant whose claim is ignored
    stay alone even if they have other candidates (no second round); a claimed centrality
    that has its own join keeps it. `rules[c]` explains the direct step of c, with precedence
    own join (P4-JOIN, P4-D25) > being claimed (P4-CLAIMED) > own claim outcome (P4-CLAIM,
    P4-CLAIM-LOST, P4-CLAIM-IGNORED) > P4-ALONE; it does not depend on the input order."""
    centrality = p.is_centrality
    incoming = np.bincount(ptr3[ptr3 >= 0], minlength=p.n)
    single = centrality & (ptr3 == -1) & (incoming == 0)
    eligible = set(scenario.phase4_levels)

    def heavier(a: int, b: int) -> bool:
        return (p.weight[a], -p.id_rank[a]) > (p.weight[b], -p.id_rank[b])

    joins: dict[int, int] = {}
    claims: dict[int, list[int]] = {}
    own: dict[int, str] = {}  # outcome of each acting single unit's own visit
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
        own[s] = outcome

    pointers = ptr3.copy()
    for s, j in joins.items():
        pointers[s] = j
    claimed_rule: dict[int, str] = {}
    result = Phase4Result(pointers)
    for j in sorted(claims, key=lambda k: p.id_rank[k]):
        claimants = claims[j]
        if j in joins:  # its own choice prevails (design, paragraph 6.6)
            for a in claimants:
                if a != joins[j]:  # a claimant that j itself joins is satisfied
                    own[a] = "P4-CLAIM-IGNORED"
                    result.ignored_claims.append((a, j))
            continue
        winner = max(claimants, key=lambda a: (p.weight[a], -p.id_rank[a]))
        for a in claimants:
            if a != winner:
                own[a] = "P4-CLAIM-LOST"
        pointers[j] = winner
        claimed_rule[j] = "P4-CLAIMED"
        if incoming[j] > 0:
            result.changed_heads.append((j, winner))
    result.ignored_claims.sort(key=lambda e: p.id_rank[e[0]])
    for c in set(own) | set(claimed_rule):
        if c in joins:
            result.rules[c] = own[c]
        else:
            result.rules[c] = claimed_rule.get(c) or own[c]
    return result
