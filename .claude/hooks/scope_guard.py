#!/usr/bin/env python3
"""CLAUDE CODE ADAPTER — PreToolUse hook on Edit|Write. Blocks an edit outside the
allowed scope. The boundary logic is the SHARED core (harness.scope) — the same
code the Layer-2 scope check uses — so the live guard and the report never disagree.

Contract: the pending tool call arrives as JSON on stdin. Exit 2 BLOCKS the call;
exit 0 allows; exit 1 is a NON-blocking error. Only 2 blocks.
"""

import json
import sys
from pathlib import Path

from harness.config import load_config
from harness.scope import classify_path


def main() -> int:
    data = json.load(sys.stdin)
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return 0
    root = Path.cwd()
    cfg = load_config(root)
    verdict = classify_path(file_path, cfg["scope"], root)
    if not verdict.allowed:
        print(
            f"Blocked: {verdict.path} is outside the allowed scope ({verdict.reason}).",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
