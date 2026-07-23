"""The acceptance worker's DECISION LOGIC — deterministic and evidence-based.

Receives the normalised story and the behaviour-suite results (a green scenario is
evidence; a failed or pending scenario means the AC is NOT met). It never marks an
AC verified without concrete evidence. Returns a validated ``AcceptanceReport``.

A ``ScenarioResult`` is the framework-independent shape the behaviour runner emits;
for MAF this is populated by the behave suite (and, later, by MAF ``LocalEvaluator``
checks and OTel span assertions carrying the same shape).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import AcceptanceReport, Criterion, Evidence, NormalizedStory, Regression


@dataclass
class ScenarioResult:
    story: str | None
    ac: str | None
    name: str
    result: str  # "passed" | "failed" | "pending"
    error: str | None = None
    evidence_type: str = "scenario"  # scenario | eval | trace


def verify_acceptance(
    story: NormalizedStory,
    scenarios: list[ScenarioResult],
    source: str = "unknown",
    base_commit: str | None = None,
    head_commit: str | None = None,
) -> AcceptanceReport:
    key = story.key
    criteria = [
        _judge(ac, [s for s in scenarios if s.story == key and s.ac == ac.id])
        for ac in story.acceptance_criteria
    ]

    # Regression: another already-shipped story's scenario now FAILED. Pending
    # scenarios of other stories are future work — informational only.
    regressions = [
        Regression(story=s.story or "?", name=s.name, result="failed", ac=s.ac)
        for s in scenarios
        if s.story != key and s.result == "failed"
    ]

    all_verified = bool(criteria) and all(c.status == "verified" for c in criteria)
    overall = "passed" if all_verified and not regressions else "failed"

    return AcceptanceReport(
        ticket=key,
        source=source,  # type: ignore[arg-type]
        baseCommit=base_commit,
        headCommit=head_commit,
        criteria=criteria,
        regressions=regressions,
        overallStatus=overall,
    )


def _judge(ac, matches: list[ScenarioResult]) -> Criterion:
    if not matches:
        return Criterion(
            id=ac.id,
            text=ac.text,
            status="not_verified",
            verdict="unclear",
            evidence=[],
            gaps=["No automated scenario maps to this AC — no executable evidence found."],
        )

    failed = [m for m in matches if m.result == "failed"]
    pending = [m for m in matches if m.result == "pending"]
    passed = [m for m in matches if m.result == "passed"]
    evidence = [Evidence(type=m.evidence_type, name=m.name, result="passed") for m in passed]  # type: ignore[arg-type]

    if failed:
        return Criterion(
            id=ac.id,
            text=ac.text,
            status="not_verified",
            verdict="FAIL",
            evidence=evidence,
            gaps=[f'Scenario "{m.name}" failed: {m.error or "assertion failed"}' for m in failed],
        )
    if pending:
        return Criterion(
            id=ac.id,
            text=ac.text,
            status="not_verified",
            verdict="FAIL",
            evidence=evidence,
            gaps=[f'Scenario "{m.name}" is pending (behaviour not implemented).' for m in pending],
        )
    return Criterion(
        id=ac.id, text=ac.text, status="verified", verdict="pass", evidence=evidence, gaps=[]
    )


def render_table(report: AcceptanceReport) -> str:
    rows = []
    for c in report.criteria:
        ev = (
            f'Scenario "{c.evidence[0].name}" passed'
            if c.verdict == "pass" and c.evidence
            else (c.gaps[0] if c.gaps else "")
        )
        rows.append(f"| {c.id} | {c.verdict:<7} | {ev} |")
    table = "\n".join(["| AC  | Verdict | Evidence |", "| --- | ------- | -------- |", *rows])
    regression = (
        "Regression: none"
        if not report.regressions
        else "Regression: " + "; ".join(f'{r.story} "{r.name}" failed' for r in report.regressions)
    )
    overall = f"Overall: {'PASS' if report.overall_status == 'passed' else 'FAIL'}"
    return f"{table}\n\n{regression}\n{overall}"
