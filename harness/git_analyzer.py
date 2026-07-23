"""Read-only git inspection used by scope checks, the change-summariser and the
acceptance worker. Never mutates the repo. Plain subprocess (no GitPython).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


def _git(args: list[str]) -> tuple[int, str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or "")


def head_commit() -> str | None:
    code, out = _git(["rev-parse", "HEAD"])
    return out.strip() if code == 0 else None


@dataclass
class BaseRef:
    ref: str | None
    commit: str | None


def base_commit(base_ref: str | None = None) -> BaseRef:
    candidates = [base_ref] if base_ref else ["origin/main", "main", "origin/master", "master"]
    for ref in candidates:
        code, out = _git(["merge-base", ref, "HEAD"])
        if code == 0 and out.strip():
            return BaseRef(ref, out.strip())
    return BaseRef(None, None)


def parse_porcelain(raw: str) -> list[str]:
    """Parse ``git status --porcelain`` (v1): 2 status columns, a space, the path.

    The raw output must NOT be trimmed, or the first line's leading status column
    is lost and the path shifts by one char. Renames "old -> new" keep the new path.
    """
    files: list[str] = []
    for line in raw.split("\n"):
        if line.strip() == "":
            continue
        path = line[3:]
        final = path.split(" -> ")[1] if " -> " in path else path
        files.append(final.strip())
    return files


def changed_files(base_ref: str | None = None) -> list[str]:
    """All paths changed vs the base commit PLUS untracked files."""
    files: set[str] = set()
    base = base_commit(base_ref)
    if base.commit:
        code, out = _git(["diff", "--name-only", base.commit, "HEAD"])
        if code == 0:
            files.update(f for f in out.strip().split("\n") if f)
    code, out = _git(["status", "--porcelain"])  # untrimmed
    if code == 0:
        files.update(parse_porcelain(out))
    return sorted(files)


def diff(base_ref: str | None = None) -> str:
    base = base_commit(base_ref)
    args = ["diff", base.commit, "--"] if base.commit else ["diff"]
    code, out = _git(args)
    return out if code == 0 else ""


def status() -> str:
    code, out = _git(["status", "--porcelain"])
    return out.strip() if code == 0 else ""
