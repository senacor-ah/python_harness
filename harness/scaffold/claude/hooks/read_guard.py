#!/usr/bin/env python3
"""CLAUDE CODE ADAPTER — PreToolUse hook on Bash|Read|Grep|Glob. A `deny`
permission blocks the Read TOOL, but not the many shell commands that also read a
file (cat, sed, head, tail, less, grep, awk, xxd, ...). This hook closes that gap
for the paths in config.read_guard.protected. Defense in depth.

Contract: exit 2 BLOCKS; exit 0 allows; exit 1 is non-blocking. Only 2 blocks.
"""

import json
import re
import sys
from pathlib import Path

from harness.config import load_config


def _is_protected(p: str, protected: list[str], root: Path) -> bool:
    if not p:
        return False
    target = (root / p).resolve()
    for name in protected:
        if "*" in name:  # glob like **/*.pfx
            if target.match(name):
                return True
            continue
        prot = (root / name).resolve()
        if target == prot or str(target).startswith(str(prot) + "/"):
            return True
    return False


def main() -> int:
    data = json.load(sys.stdin)
    tool = data.get("tool_name")
    ti = data.get("tool_input") or {}
    root = Path.cwd()
    protected = load_config(root)["read_guard"]["protected"]

    for p in (ti.get("file_path"), ti.get("path"), ti.get("notebook_path")):
        if _is_protected(p, protected, root):
            print(f"Blocked: {p} is protected and must not be read (read-guard).", file=sys.stderr)
            return 2

    if tool == "Bash" and isinstance(ti.get("command"), str):
        cmd = ti["command"]
        for name in protected:
            token = name.replace("**/", "").replace("*", "")
            esc = re.escape(token)
            if re.search(rf"(?:^|[\s'\"=./]){esc}(?:$|[\s'\"/])", cmd):
                print(f"Blocked: command references a protected path ({name}).", file=sys.stderr)
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
