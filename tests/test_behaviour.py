from harness.behaviour import _scenario_status, _tag_value


def test_tag_value_strips_prefix():
    assert _tag_value(["story:PROJ-1234", "ac:AC1"], "story") == "PROJ-1234"
    assert _tag_value(["story:PROJ-1234", "ac:AC1"], "ac") == "AC1"
    assert _tag_value(["other"], "story") is None


def _steps(*statuses):
    return {"steps": [{"result": {"status": s}} for s in statuses]}


def test_all_passed_is_passed():
    assert _scenario_status(_steps("passed", "passed")) == "passed"


def test_any_failed_is_failed():
    assert _scenario_status(_steps("passed", "failed", "skipped")) == "failed"


def test_undefined_is_pending():
    assert _scenario_status(_steps("undefined", "skipped")) == "pending"


def test_failed_beats_undefined():
    # An implemented-but-wrong step (failed) outranks an undefined one.
    assert _scenario_status(_steps("failed", "undefined")) == "failed"


def test_step_without_result_is_pending():
    assert _scenario_status({"steps": [{"name": "x"}]}) == "pending"


def test_no_steps_is_pending():
    assert _scenario_status({"steps": []}) == "pending"
