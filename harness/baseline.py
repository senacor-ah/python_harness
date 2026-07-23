"""Baseline read/write. The baseline is the LOCAL snapshot of the Jira story the
work was agreed against. It lives under .harness/baseline/ and is git-ignored:
stories live in Jira, never in the develop repo. The harness never updates a
baseline automatically — only the explicit, logged ``harness accept-drift``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .models import Baseline, NormalizedStory

HARNESS_VERSION = "1.0.0"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def baseline_path(key: str, root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".harness" / "baseline" / f"{key}.json"


def load_baseline(key: str, root: Path | None = None) -> Baseline | None:
    path = baseline_path(key, root)
    if not path.exists():
        return None
    return Baseline.model_validate_json(path.read_text())


def save_baseline(baseline: Baseline, root: Path | None = None) -> Path:
    path = baseline_path(baseline.story.key, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(baseline.model_dump_json(by_alias=True, indent=2) + "\n")
    return path


def make_baseline(
    story: NormalizedStory, branch: str, git_commit: str | None, source: str
) -> Baseline:
    return Baseline(
        story=story,
        jiraUpdated=story.updated,
        createdAt=now_iso(),
        gitCommit=git_commit,
        branch=branch,
        harnessVersion=HARNESS_VERSION,
        source=source,  # type: ignore[arg-type]
    )


def log_drift_accept(root: Path, message: str) -> Path:
    path = (root or Path.cwd()) / ".harness" / "runtime" / "drift-accept.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(message + "\n")
    return path
