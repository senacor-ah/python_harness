# Python + MAF feature harness

A Python 3.12 port of the agent-independent feature harness, targeting
**Microsoft Agent Framework (MAF)** projects on Azure Functions. Standalone dev/CI
tool — **not** shipped inside the agent containers. See
[`../docs/python-maf-port-plan.md`](../docs/python-maf-port-plan.md) for the full plan.

## Status — Phases 1–3 + 5 complete (57 tests, ruff-clean, GREEN gate)

- **Core:** exit codes, config (PyYAML), branch→key, scope (path-boundary), git
  analyzer (subprocess), credentials (keyring + env fallback).
- **Models:** Pydantic v2 for story / baseline / acceptance report, with the report
  **invariants enforced in code** (`verified` requires evidence; `passed` forbids
  regressions / unverified ACs) — a malformed report cannot be constructed.
- **Jira:** read-only httpx client + labelled fixtures (offline/CI).
- **Drift:** structural detector (critical/high/medium/low/none), `critical|high` blocks.
- **Acceptance logic:** per-AC verdict from evidence, regression detection (AC11/12/13).
- **Four verification layers** (`verify` / `gate`):
  - **Quality** — ruff (format+lint), mypy, **import-linter** architecture contracts,
    and the Azure-Functions worker guard.
  - **Scope** — every changed path checked against `scope.allowed`/`denied`.
  - **Behaviour** — a **behave** suite driving the layered `app/` demo, mapped to ACs
    (passed/failed/pending, cumulative → regressions surface).
  - **Reporting** — one GREEN/RED verdict.
- **Adapters:** `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, and
  Python Claude Code hooks (`session_prepare`, `scope_guard`, `read_guard`,
  `quality_hook`) + subagents — all thin wrappers over `python -m harness`.
- **CI:** `.github/workflows/harness.yml` runs the same CLI.

**Next — Phase 4 (real MAF wiring):** replace the stub agent in `app/agents/` with a
MAF `ChatAgent` + `@tool`, and back the behaviour tool-call assertions with MAF
`LocalEvaluator` (`tool_called_check` / `tool_call_args_match`). This is a contained
change, **blocked only on the MAF rc1 API verification checklist** (plan §9) — run
the ~8 `inspect.signature` probes against the installed wheel first.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

python -m harness status          # branch / baseline / credential state
python -m harness prepare         # load story (fixture), create baseline, write context
python -m harness check-drift     # compare current Jira story to baseline
pytest -q                         # 45 tests
ruff check . && ruff format --check .
```

Runs in **fixture mode** by default (`.harness/config.yaml`) — reads
`.harness/fixtures/PROJ-1234.json`, a labelled stand-in for the Jira REST response.
Set `jira.base_url`, run `harness auth jira`, and `fixture_mode: false` for real Jira.

## Exit codes

`0` ok · `2` warning · `3` blocking drift · `4` jira/auth · `5` invalid branch ·
`6` verify failed — identical to the Node reference harness.
