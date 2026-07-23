from harness.acceptance_verifier import ScenarioResult, verify_acceptance
from harness.models import AcceptanceCriterion, NormalizedStory

STORY = NormalizedStory(
    key="PROJ-1234",
    acceptanceCriteria=[
        AcceptanceCriterion(id="AC1", text="A PDF is downloaded."),
        AcceptanceCriterion(id="AC2", text="Unauthorized users get 403."),
    ],
)


def sr(ac, result, story="PROJ-1234", name="s", error=None):
    return ScenarioResult(story=story, ac=ac, name=name, result=result, error=error)


def test_passing_scenarios_verify_with_evidence():
    r = verify_acceptance(STORY, [sr("AC1", "passed"), sr("AC2", "passed")], source="fixture")
    assert r.overall_status == "passed"
    assert all(c.status == "verified" and c.evidence for c in r.criteria)


def test_ac11_failed_scenario_never_verified():
    r = verify_acceptance(
        STORY, [sr("AC1", "passed"), sr("AC2", "failed", error="got 200")], source="fixture"
    )
    ac2 = next(c for c in r.criteria if c.id == "AC2")
    assert ac2.status == "not_verified" and ac2.verdict == "FAIL"
    assert r.overall_status == "failed"


def test_pending_current_ac_not_met():
    r = verify_acceptance(STORY, [sr("AC1", "passed"), sr("AC2", "pending")], source="fixture")
    assert next(c for c in r.criteria if c.id == "AC2").verdict == "FAIL"
    assert r.overall_status == "failed"


def test_ac12_regression_from_other_shipped_story():
    scenarios = [
        sr("AC1", "passed"),
        sr("AC2", "passed"),
        sr("AC1", "failed", story="PROJ-1000", name="login", error="no token"),
    ]
    r = verify_acceptance(STORY, scenarios, source="fixture")
    assert len(r.regressions) == 1 and r.regressions[0].story == "PROJ-1000"
    assert r.overall_status == "failed"


def test_ac13_pending_future_story_not_regression():
    scenarios = [
        sr("AC1", "passed"),
        sr("AC2", "passed"),
        sr("AC1", "pending", story="PROJ-2000", name="email"),
    ]
    r = verify_acceptance(STORY, scenarios, source="fixture")
    assert r.regressions == []
    assert r.overall_status == "passed"


def test_no_scenario_is_unclear_never_verified():
    r = verify_acceptance(STORY, [sr("AC1", "passed")], source="fixture")
    ac2 = next(c for c in r.criteria if c.id == "AC2")
    assert ac2.verdict == "unclear" and ac2.status == "not_verified" and ac2.gaps
    assert r.overall_status == "failed"
