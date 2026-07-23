#!/usr/bin/env python3
"""CLAUDE CODE ADAPTER — PostToolUse hook on Edit|Write. After a product-code edit
it (1) formats the file with ruff — never blocks — and (2) lints it; a real lint
violation BLOCKS (exit 2). Formatting failures are non-blocking by design.
"""

import json
import subprocess
import sys
from pathlib import Path

from harness.config import load_config
from harness.scope import classify_path


def main() -> int:
    data = json.load(sys.stdin)
    file_path = (data.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return 0
    root = Path.cwd()
    cfg = load_config(root)
    target = (root / file_path).resolve()

    # Only act on in-scope product source under app/.
    if not classify_path(file_path, cfg["scope"], root).allowed:
        return 0
    if not (str(target).startswith(str((root / "app").resolve()) + "/") and target.suffix == ".py"):
        return 0

    # 1) Format — never blocks.
    subprocess.run(["ruff", "format", str(target)], cwd=root, capture_output=True)
    # 2) Lint — block on failure.
    lint = subprocess.run(["ruff", "check", str(target)], cwd=root, capture_output=True, text=True)
    if lint.returncode != 0:
        sys.stderr.write(lint.stdout + lint.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
