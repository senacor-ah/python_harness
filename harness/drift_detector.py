"""Structural drift detection between a saved baseline story and the current Jira
story. The STRUCTURAL diff is authoritative. Because both stories are normalised,
a presentation-only edit produces NO structural change and never a critical drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import NormalizedStory

ORDER = ["none", "low", "medium", "high", "critical"]


def max_level(a: str, b: str) -> str:
    return ORDER[max(ORDER.index(a), ORDER.index(b))]


@dataclass
class Change:
    field: str
    type: str
    category: str
    detail: str
    id: str | None = None


@dataclass
class DriftResult:
    level: str
    blocking: bool
    changes: list[Change] = field(default_factory=list)


def detect_drift(baseline: NormalizedStory, current: NormalizedStory, cfg: dict) -> DriftResult:
    changes: list[Change] = []

    base_acs = {a.id: a.text for a in baseline.acceptance_criteria}
    cur_acs = {a.id: a.text for a in current.acceptance_criteria}

    # Acceptance criteria: any add / remove / textual change is CRITICAL.
    for ac_id, text in cur_acs.items():
        if ac_id not in base_acs:
            changes.append(Change("acceptanceCriteria", "added", "critical", text, ac_id))
        elif base_acs[ac_id] != text:
            changes.append(
                Change(
                    "acceptanceCriteria",
                    "changed",
                    "critical",
                    f'"{base_acs[ac_id]}" -> "{text}"',
                    ac_id,
                )
            )
    for ac_id, text in base_acs.items():
        if ac_id not in cur_acs:
            changes.append(Change("acceptanceCriteria", "removed", "critical", text, ac_id))

    # Description / summary: HIGH.
    if baseline.description != current.description:
        changes.append(Change("description", "changed", "high", "description text changed"))
    if baseline.summary != current.summary:
        changes.append(
            Change("summary", "changed", "high", f'"{baseline.summary}" -> "{current.summary}"')
        )

    # Priority / status / components: MEDIUM.
    for f in ("priority", "status"):
        if getattr(baseline, f) != getattr(current, f):
            changes.append(
                Change(f, "changed", "medium", f"{getattr(baseline, f)} -> {getattr(current, f)}")
            )
    if baseline.components != current.components:
        changes.append(
            Change(
                "components",
                "changed",
                "medium",
                _diff_arrays(baseline.components, current.components),
            )
        )

    # Labels: LOW.
    if baseline.labels != current.labels:
        changes.append(
            Change("labels", "changed", "low", _diff_arrays(baseline.labels, current.labels))
        )

    level = "none"
    for c in changes:
        level = max_level(level, c.category)
    blocking_levels = cfg.get("drift", {}).get("blocking_levels", ["critical", "high"])
    blocking = level in blocking_levels and level != "none"
    return DriftResult(level=level, blocking=blocking, changes=changes)


def _diff_arrays(a: list[str], b: list[str]) -> str:
    added = [x for x in b if x not in a]
    removed = [x for x in a if x not in b]
    parts = []
    if added:
        parts.append(f"+[{', '.join(added)}]")
    if removed:
        parts.append(f"-[{', '.join(removed)}]")
    return " ".join(parts) or "reordered"
