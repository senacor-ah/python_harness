"""Load and give typed access to .harness/config.yaml.

Every module reads configuration through here so there is exactly one source of
truth. We use PyYAML ``safe_load`` (read-only); the config is never rewritten by
the harness, so comment-preserving round-tripping (ruamel) is not required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_BRANCH_PATTERN = r"^feature/(?P<ticket>[A-Z][A-Z0-9]+-\d+)$"


def repo_root() -> Path:
    return Path.cwd()


def config_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / ".harness" / "config.yaml"


def load_config(root: Path | None = None) -> dict[str, Any]:
    path = config_path(root)
    if not path.exists():
        raise FileNotFoundError(f"Harness config not found at {path}")
    cfg = yaml.safe_load(path.read_text()) or {}
    return _with_defaults(cfg)


def _with_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    cfg.setdefault("branch", {})
    cfg["branch"].setdefault("pattern", DEFAULT_BRANCH_PATTERN)
    cfg.setdefault("jira", {})
    cfg["jira"].setdefault("acceptance_criteria_fields", ["description"])
    cfg["jira"].setdefault("fixtures_dir", ".harness/fixtures")
    cfg.setdefault("credentials", {})
    cfg["credentials"].setdefault("service", "harness-jira")
    cfg["credentials"].setdefault("email_env", "JIRA_EMAIL")
    cfg["credentials"].setdefault("token_env", "JIRA_API_TOKEN")
    cfg.setdefault("scope", {})
    cfg["scope"].setdefault("allowed", [])
    cfg["scope"].setdefault("denied", [])
    cfg.setdefault("read_guard", {})
    cfg["read_guard"].setdefault("protected", [])
    cfg.setdefault("quality", {})
    cfg["quality"].setdefault("commands", [])
    cfg.setdefault("behaviour", {})
    cfg["behaviour"].setdefault("features_dir", "features")
    cfg["behaviour"].setdefault("steps_dir", "features/steps")
    cfg.setdefault("drift", {})
    cfg["drift"].setdefault("blocking_levels", ["critical", "high"])
    return cfg
