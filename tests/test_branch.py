from harness.branch import detect_ticket, parse_branch
from harness.exit_codes import Exit

PATTERN = r"^feature/(?P<ticket>[A-Z][A-Z0-9]+-\d+)$"


def test_valid_feature_branch():
    r = parse_branch("feature/PROJ-1234", PATTERN)
    assert r.ok and r.ticket == "PROJ-1234"


def test_multiletter_key_with_digits():
    assert parse_branch("feature/AB12-9", PATTERN).ticket == "AB12-9"


def test_invalid_format_rejected():
    r = parse_branch("bugfix/PROJ-1", PATTERN)
    assert not r.ok and r.code == Exit.INVALID_BRANCH


def test_no_ticket_rejected():
    assert not parse_branch("feature/no-ticket-here", PATTERN).ok


def test_lowercase_key_rejected():
    assert not parse_branch("feature/proj-1234", PATTERN).ok


def test_detached_head():
    r = detect_ticket(PATTERN, git_branch="HEAD")
    assert not r.ok and r.code == Exit.INVALID_BRANCH and "detached" in r.reason


def test_no_git_repo():
    r = detect_ticket(PATTERN, git_branch=None)
    assert not r.ok and r.code == Exit.INVALID_BRANCH and "not a git repository" in r.reason
