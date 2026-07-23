from harness.models import AcceptanceReport, Criterion, Evidence
from harness.report_builder import ScopeLayer, build_final_report
from harness.test_runner import GateResult, QualityResult


def _quality(passed=True):
    return QualityResult(
        passed=passed,
        results=[GateResult("lint", "ruff check", 0 if passed else 1, passed, "")],
    )


def _report_passed():
    return AcceptanceReport(
        ticket="PROJ-1234",
        criteria=[
            Criterion(
                id="AC1",
                text="x",
                status="verified",
                verdict="pass",
                evidence=[Evidence(type="scenario", name="s", result="passed")],
            )
        ],
        overallStatus="passed",
    )


def _report_failed():
    return AcceptanceReport(
        ticket="PROJ-1234",
        criteria=[
            Criterion(id="AC1", text="x", status="not_verified", verdict="FAIL", gaps=["nope"])
        ],
        overallStatus="failed",
    )


def test_green_only_when_all_four_layers_ok():
    final = build_final_report(_quality(True), ScopeLayer(True, [], []), _report_passed())
    assert final.green and "GREEN" in final.text and not final.failing


def test_quality_fail_makes_red():
    final = build_final_report(_quality(False), ScopeLayer(True, [], []), _report_passed())
    assert not final.green and "Quality" in final.failing


def test_scope_fail_names_paths():
    scope = ScopeLayer(
        False, ["app/services/x.py"], [{"path": "app/services/x.py", "reason": "denied"}]
    )
    final = build_final_report(_quality(True), scope, _report_passed())
    assert not final.green and "Scope" in final.failing and "app/services/x.py" in final.text


def test_behaviour_fail_makes_red():
    final = build_final_report(_quality(True), ScopeLayer(True, [], []), _report_failed())
    assert not final.green and "Behaviour" in final.failing


def test_red_line_names_every_failing_layer():
    scope = ScopeLayer(False, ["x"], [{"path": "x", "reason": "denied"}])
    final = build_final_report(_quality(False), scope, _report_failed())
    assert set(final.failing) == {"Quality", "Scope", "Behaviour"}
    assert "RED — Quality, Scope, Behaviour" in final.text
