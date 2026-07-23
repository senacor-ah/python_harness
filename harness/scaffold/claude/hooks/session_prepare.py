#!/usr/bin/env python3
"""CLAUDE CODE ADAPTER — SessionStart hook. A THIN wrapper: it runs the core CLI
`harness prepare --format agent` and injects the story context. All business logic
lives in the CLI. On a blocking drift (exit 3) it refuses to inject an
implementation-ready context.
"""

import json
import subprocess
import sys


def emit(context: str, note: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"{note}\n\n{context}",
        }
    }
    sys.stdout.write(json.dumps(payload))


def main() -> int:
    r = subprocess.run(
        [sys.executable, "-m", "harness", "prepare", "--format", "agent"],
        capture_output=True,
        text=True,
    )
    text = f"{r.stdout}{r.stderr}".strip()
    code = r.returncode
    if code == 0:
        emit(text, "Harness ready. Story context below. Run `harness verify` before completion.")
    elif code == 3:
        emit(
            text,
            "⛔ BLOCKING JIRA DRIFT — do NOT start implementation. "
            "Resolve via `harness accept-drift`.",
        )
    elif code == 5:
        emit(text, "Not on a feature/<JIRA-KEY> branch — the harness is idle.")
    else:
        emit(text, "Harness could not prepare (see message). Fix before editing code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
