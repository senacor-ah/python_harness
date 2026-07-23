from harness.git_analyzer import parse_porcelain


def test_leading_space_status_column_preserved():
    # Regression: the raw status output must NOT be trimmed, or the first line's
    # leading " " column is lost and the path shifts by one char.
    raw = " M workflows/router.py\n?? tools/new_tool.py\n"
    assert parse_porcelain(raw) == ["workflows/router.py", "tools/new_tool.py"]


def test_staged_and_untracked_mix():
    raw = "M  agents/a.py\nA  agents/b.py\n?? features/x.feature\n"
    assert parse_porcelain(raw) == ["agents/a.py", "agents/b.py", "features/x.feature"]


def test_rename_keeps_new_path():
    assert parse_porcelain("R  tools/old.py -> tools/new.py\n") == ["tools/new.py"]


def test_blank_lines_ignored():
    assert parse_porcelain("\n M tools/a.py\n\n") == ["tools/a.py"]
