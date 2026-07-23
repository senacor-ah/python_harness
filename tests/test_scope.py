from pathlib import Path

from harness.scope import classify_path

ROOT = Path("/repo")
SCOPE = {
    "allowed": ["workflows/**", "agents/**", "tools/**", "features/**"],
    "denied": [
        "auth/**",
        "services/api/**",
        "middleware/masking.py",
        "harness/**",
        ".harness/config.yaml",
    ],
}


def test_allowed_path():
    assert classify_path("workflows/balance_info_workflow/router.py", SCOPE, ROOT).allowed


def test_denied_auth():
    assert not classify_path("auth/jwt_utils.py", SCOPE, ROOT).allowed


def test_denied_mtls_client():
    assert not classify_path("services/api/cpp/client.py", SCOPE, ROOT).allowed


def test_similar_named_sibling_not_allowed_by_substring():
    # "workflows-notes/x" must not be treated as inside "workflows/"
    assert not classify_path("workflows-notes/x.py", SCOPE, ROOT).allowed


def test_similar_named_denied_sibling_not_false_positive():
    v = classify_path("services/api-notes/x.py", SCOPE, ROOT)
    assert not v.allowed and "outside the allowed scope" in v.reason


def test_path_traversal_into_denied():
    assert not classify_path("workflows/../auth/jwt_utils.py", SCOPE, ROOT).allowed


def test_absolute_path_into_denied():
    assert not classify_path("/repo/auth/jwt_utils.py", SCOPE, ROOT).allowed


def test_exact_file_deny():
    assert not classify_path("middleware/masking.py", SCOPE, ROOT).allowed
    v = classify_path("middleware/timing.py", SCOPE, ROOT)
    assert not v.allowed and "outside the allowed scope" in v.reason  # not a denied match


def test_deny_precedence_over_allow():
    s = {"allowed": ["**"], "denied": ["harness/**"]}
    assert not classify_path("harness/cli.py", s, ROOT).allowed
    assert classify_path("anything/else.py", s, ROOT).allowed
