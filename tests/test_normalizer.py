from harness.story_normalizer import (
    adf_to_text,
    normalize_story,
    normalize_text,
    split_criteria,
)

CFG = {"jira": {"acceptance_criteria_fields": ["customfield_10401", "description"]}}


def _adf_doc(*paras):
    return {"type": "doc", "version": 1, "content": list(paras)}


def _para(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _bullets(*items):
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "bulletList",
                "content": [{"type": "listItem", "content": [_para(t)]} for t in items],
            }
        ],
    }


def test_adf_flattened():
    assert normalize_text(adf_to_text(_adf_doc(_para("Hello"), _para("World")))) == "Hello\nWorld"


def test_empty_description():
    s = normalize_story({"key": "PROJ-1", "fields": {"summary": "S", "description": None}}, CFG)
    assert s.description == ""


def test_custom_field_acs_get_stable_ids():
    s = normalize_story(
        {
            "key": "PROJ-1",
            "fields": {"summary": "S", "customfield_10401": _bullets("First AC", "Second AC")},
        },
        CFG,
    )
    assert [(a.id, a.text) for a in s.acceptance_criteria] == [
        ("AC1", "First AC"),
        ("AC2", "Second AC"),
    ]


def test_labels_and_components_sorted():
    s = normalize_story(
        {
            "key": "PROJ-1",
            "fields": {
                "summary": "S",
                "labels": ["z", "a", "m"],
                "components": [{"name": "web"}, {"name": "api"}],
            },
        },
        CFG,
    )
    assert s.labels == ["a", "m", "z"]
    assert s.components == ["api", "web"]


def test_presentation_only_change_normalised_away():
    a = split_criteria(normalize_text("- One thing\n-   One thing again"))
    b = split_criteria(normalize_text("1) One thing\n2)    One thing again"))
    assert [(x.id, x.text) for x in a] == [(x.id, x.text) for x in b]


def test_first_nonempty_ac_field_wins():
    s = normalize_story(
        {"key": "PROJ-1", "fields": {"summary": "S", "description": _bullets("Desc AC")}}, CFG
    )
    assert [(a.id, a.text) for a in s.acceptance_criteria] == [("AC1", "Desc AC")]
