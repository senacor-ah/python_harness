@AGENTS.md

This repository uses the shared, agent-independent feature harness. **The rules in
`AGENTS.md` are authoritative** — everything below is only Claude-specific wiring
around the same `python -m harness` CLI.

## Claude-specific notes

- A **SessionStart** hook (`.claude/hooks/session_prepare.py`) runs
  `harness prepare --format agent` and injects the current story context. On a
  blocking drift it refuses to inject an implementation-ready context.
- **PreToolUse** hooks enforce boundaries mechanically: `scope_guard.py` blocks
  edits outside the allowed scope (exit 2), `read_guard.py` blocks reads of
  protected/secret paths (including via shell `cat`/`sed`/`grep`).
- A **PostToolUse** hook (`quality_hook.py`) formats (ruff, non-blocking) then lints
  (ruff, blocking) edited product files.
- For final verification, dispatch the isolated **`acceptance-reviewer`** subagent —
  it verifies each AC against behaviour evidence in its own context.
- The **`change-summarizer`** subagent gives a read-only orientation summary.

These hooks and subagents are thin **adapters**. All logic lives in `harness/` —
never re-implement it here. Before editing code, ensure `harness prepare` succeeded;
before declaring completion, run `harness verify` (or `harness gate`).
