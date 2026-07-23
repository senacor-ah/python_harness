from harness.drift_detector import detect_drift
from harness.models import AcceptanceCriterion, NormalizedStory

CFG = {"drift": {"blocking_levels": ["critical", "high"]}}


def story(**over):
    base = dict(
        key="PROJ-1",
        summary="Download invoice",
        description="As a user I download my invoice.",
        acceptanceCriteria=[
            AcceptanceCriterion(id="AC1", text="A PDF is downloaded."),
            AcceptanceCriterion(id="AC2", text="Unauthorized users get 403."),
        ],
        status="In Progress",
        priority="High",
        labels=["billing"],
        components=["web"],
    )
    base.update(over)
    return NormalizedStory(**base)


def test_ac_added_is_critical_blocking():
    cur = story(
        acceptanceCriteria=[
            AcceptanceCriterion(id="AC1", text="A PDF is downloaded."),
            AcceptanceCriterion(id="AC2", text="Unauthorized users get 403."),
            AcceptanceCriterion(id="AC3", text="Every download creates an audit event."),
        ]
    )
    d = detect_drift(story(), cur, CFG)
    assert d.level == "critical" and d.blocking
    assert any(c.type == "added" and c.id == "AC3" for c in d.changes)


def test_ac_removed_is_critical():
    cur = story(acceptanceCriteria=[AcceptanceCriterion(id="AC1", text="A PDF is downloaded.")])
    assert detect_drift(story(), cur, CFG).level == "critical"


def test_ac_text_changed_is_critical():
    cur = story(
        acceptanceCriteria=[
            AcceptanceCriterion(id="AC1", text="A signed PDF is downloaded."),
            AcceptanceCriterion(id="AC2", text="Unauthorized users get 403."),
        ]
    )
    assert detect_drift(story(), cur, CFG).level == "critical"


def test_label_only_is_low_nonblocking():
    d = detect_drift(story(), story(labels=["billing", "urgent"]), CFG)
    assert d.level == "low" and not d.blocking


def test_formatting_only_is_none():
    d = detect_drift(story(), story(), CFG)
    assert d.level == "none" and not d.blocking


def test_priority_status_is_medium():
    d = detect_drift(story(), story(priority="Low", status="Done"), CFG)
    assert d.level == "medium" and not d.blocking


def test_description_change_is_high_blocking():
    d = detect_drift(story(), story(description="Totally new scope constraint."), CFG)
    assert d.level == "high" and d.blocking
