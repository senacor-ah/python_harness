"""The report invariants are enforced by Pydantic, so an invalid report cannot even
be constructed. Each test asserts a ValidationError is raised."""

import pytest
from pydantic import ValidationError

from harness.models import AcceptanceReport, Criterion, Evidence

GOOD_EVIDENCE = [Evidence(type="scenario", name="s", result="passed")]


def _report(**over):
    base = dict(
        ticket="PROJ-1234",
        source="fixture",
        criteria=[
            Criterion(id="AC1", text="x", status="verified", verdict="pass", evidence=GOOD_EVIDENCE)
        ],
        regressions=[],
        overallStatus="passed",
    )
    base.update(over)
    return AcceptanceReport(**base)


def test_verified_without_evidence_rejected():
    with pytest.raises(ValidationError, match="requires at least one evidence"):
        Criterion(id="AC1", text="x", status="verified", verdict="pass", evidence=[])


def test_not_verified_without_gap_rejected():
    with pytest.raises(ValidationError, match="requires a gap"):
        Criterion(id="AC1", text="x", status="not_verified", verdict="FAIL", evidence=[], gaps=[])


def test_overall_passed_with_regression_rejected():
    with pytest.raises(ValidationError, match="forbids any regression"):
        _report(regressions=[{"story": "PROJ-1000", "name": "login", "result": "failed"}])


def test_overall_passed_with_unverified_ac_rejected():
    with pytest.raises(ValidationError, match="requires every AC verified"):
        _report(
            overallStatus="passed",
            criteria=[
                Criterion(
                    id="AC1", text="x", status="verified", verdict="pass", evidence=GOOD_EVIDENCE
                ),
                Criterion(
                    id="AC2",
                    text="y",
                    status="not_verified",
                    verdict="unclear",
                    gaps=["no scenario"],
                ),
            ],
        )


def test_bad_ticket_rejected():
    with pytest.raises(ValidationError):
        _report(ticket="proj-1")


def test_wellformed_report_ok_and_roundtrips():
    r = _report()
    assert r.overall_status == "passed"
    js = r.to_json()
    assert '"overallStatus": "passed"' in js and '"acceptanceCriteria"' not in js
