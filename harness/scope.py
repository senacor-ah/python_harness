"""Scope boundary logic — the SINGLE implementation shared by the scope-guard
hook (live, per-edit) and the Layer-2 scope check in ``harness verify``.

Uses normalised absolute paths and real path-boundary matching, never a naive
substring test like ``"harness/" in path``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScopeVerdict:
    allowed: bool
    reason: str
    path: str


def _glob_matcher(pattern: str, root: Path) -> Callable[[Path], bool]:
    """Turn a glob into a predicate over an absolute target path.

    Supported shapes (exactly what this harness uses):
      - ``dir/**``     -> the directory and everything under it
      - ``dir/*.ext``  -> direct children of dir with that extension
      - ``**/*.ext``   -> any file with that extension, at any depth
      - ``exact/file`` -> that one file
    """
    if pattern == "**" or pattern.startswith("**/*."):
        ext = pattern.split("**/*.", 1)[1] if pattern != "**" else None
        return lambda target: ext is None or target.name.endswith("." + ext)
    if pattern.endswith("/**"):
        base = (root / pattern[:-3]).resolve()
        return lambda target: target == base or _is_within(target, base)
    if "/*." in pattern:
        dir_part, ext_part = pattern.split("/*.", 1)
        base = (root / dir_part).resolve()

        def _direct_child(target: Path) -> bool:
            return target.parent == base and target.name.endswith("." + ext_part)

        return _direct_child
    exact = (root / pattern).resolve()
    return lambda target: target == exact


def _is_within(target: Path, base: Path) -> bool:
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def classify_path(file_path: str, scope: dict, root: Path | None = None) -> ScopeVerdict:
    """Decide whether editing ``file_path`` is allowed under the scope config.

    Precedence: an explicit ``denied`` match always blocks. Otherwise, a non-empty
    ``allowed`` list must match; an empty allow-list means "allow anything not denied".
    """
    root = (root or Path.cwd()).resolve()
    target = (root / file_path).resolve()

    denied = scope.get("denied", []) or []
    for pat in denied:
        if _glob_matcher(pat, root)(target):
            return ScopeVerdict(False, f'matches denied scope "{pat}"', _rel_or_abs(target, root))

    allowed = scope.get("allowed", []) or []
    if not allowed:
        return ScopeVerdict(True, "no allow-list configured; not denied", _rel_or_abs(target, root))
    for pat in allowed:
        if _glob_matcher(pat, root)(target):
            return ScopeVerdict(True, f'matches allowed scope "{pat}"', _rel_or_abs(target, root))
    return ScopeVerdict(False, "outside the allowed scope", _rel_or_abs(target, root))


def _rel_or_abs(target: Path, root: Path) -> str:
    try:
        return str(target.relative_to(root))
    except ValueError:
        return str(target)
