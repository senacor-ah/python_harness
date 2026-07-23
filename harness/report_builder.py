"""Builds the four-layer GREEN/RED report and the read-only change summary. The
report is a pure function of the layer results, so ``Overall: GREEN`` is impossible
unless all four layers are OK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .git_analyzer import changed_files
from .models import AcceptanceReport
from .scope import classify_path
from .test_runner import QualityResult

TICK = "✓"  # ✓
CROSS = "✗"  # ✗


@dataclass
class ScopeLayer:
    passed: bool
    files: list[str]
    violations: list[dict] = field(default_factory=list)


def check_scope_layer(cfg: dict, root: Path | None = None) -> ScopeLayer:
    root = root or Path.cwd()
    files = changed_files()
    violations = []
    for f in files:
        v = classify_path(f, cfg["scope"], root)
        if not v.allowed:
            violations.append({"path": f, "reason": v.reason})
    return ScopeLayer(passed=not violations, files=files, violations=violations)


@dataclass
class FinalReport:
    text: str
    green: bool
    failing: list[str]


def build_final_report(
    quality: QualityResult, scope: ScopeLayer, behaviour_report: AcceptanceReport
) -> FinalReport:
    failing: list[str] = []

    if quality.passed:
        q_line = f"{TICK} " + ", ".join(f"{r.name} 0" for r in quality.results)
    else:
        q_line = f"{CROSS} " + ", ".join(
            f"{r.name} {0 if r.passed else r.exit_code}" for r in quality.results
        )
        failing.append("Quality")

    if scope.passed:
        s_line = f"{TICK} only allowed paths touched"
    else:
        s_line = f"{CROSS} " + ", ".join(v["path"] for v in scope.violations) + " touched"
        failing.append("Scope")

    b_passed = behaviour_report.overall_status == "passed"
    b_line = (
        f"{TICK} acceptance verifier PASS ({behaviour_report.ticket})"
        if b_passed
        else f"{CROSS} acceptance verifier FAIL ({behaviour_report.ticket})"
    )
    if not b_passed:
        failing.append("Behaviour")

    r_line = f"{TICK} summary generated"
    overall = "GREEN" if not failing else f"RED — {', '.join(failing)}"

    text = "\n".join(
        [
            f"Quality:   {q_line}",
            f"Scope:     {s_line}",
            f"Behaviour: {b_line}",
            f"Reporting: {r_line}",
            f"Overall:   {overall}",
        ]
    )
    return FinalReport(text=text, green=not failing, failing=failing)


def build_change_summary(cfg: dict, root: Path | None = None) -> dict:
    root = root or Path.cwd()
    files = changed_files()
    lines, surprising = [], []
    for f in files:
        v = classify_path(f, cfg["scope"], root)
        flag = "" if v.allowed else "  ⚠ outside allowed scope"
        lines.append(f"- {f}{flag}")
        if not v.allowed:
            surprising.append(f"- {f} — {v.reason}")
    text = "\n".join(
        [
            "What changed",
            f"- {len(files)} file(s) modified on this branch" if files else "- no changes detected",
            "",
            "Files touched",
            *(lines or ["- none"]),
            "",
            "Anything surprising",
            *(surprising or ["- nothing surprising"]),
        ]
    )
    return {"files": files, "text": text}
