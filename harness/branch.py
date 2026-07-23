"""Deterministic branch -> Jira-key detection. No LLM, no network.

Pure parsing of ``git`` output, fully unit-testable.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from .exit_codes import Exit


@dataclass
class BranchResult:
    ok: bool
    ticket: str | None = None
    branch: str | None = None
    code: Exit | None = None
    reason: str | None = None


def parse_branch(branch: str, pattern_source: str) -> BranchResult:
    """Given a branch name and a regex source, return the ticket or a typed error."""
    m = re.search(pattern_source, branch)
    ticket = m.group("ticket") if m and "ticket" in (m.groupdict() or {}) else None
    if not ticket:
        return BranchResult(
            ok=False,
            code=Exit.INVALID_BRANCH,
            reason=f'branch "{branch}" does not match {pattern_source}',
            branch=branch,
        )
    return BranchResult(ok=True, ticket=ticket, branch=branch)


def detect_ticket(pattern: str, git_branch: str | None | object = ...) -> BranchResult:
    """Resolve the current ticket.

    ``git_branch`` sentinel ``...`` (Ellipsis) means "read git now"; an explicit
    ``None`` means the caller asserts "no repo".
    """
    branch = current_git_branch() if git_branch is ... else git_branch  # type: ignore[assignment]
    if branch is None:
        return BranchResult(ok=False, code=Exit.INVALID_BRANCH, reason="not a git repository")
    if branch == "HEAD":
        return BranchResult(
            ok=False, code=Exit.INVALID_BRANCH, reason="detached HEAD — check out a feature branch"
        )
    return parse_branch(branch, pattern)


def current_git_branch() -> str | None:
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout.strip()
