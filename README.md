# Python + MAF feature harness

A Python 3.12 port of the agent-independent feature harness, targeting
**Microsoft Agent Framework (MAF)** projects on Azure Functions. Standalone dev/CI
tool — **not** shipped inside the agent containers. See
[`../docs/python-maf-port-plan.md`](../docs/python-maf-port-plan.md) for the full plan.

## Status — Phase 1 + 2 complete

Implemented and tested (45 tests, ruff-clean):

- **Core:** exit codes, config (PyYAML), branch→key, scope (path-boundary), git
  analyzer (subprocess), credentials (keyring + env fallback).
- **Models:** Pydantic v2 for story / baseline / acceptance report, with the report
  **invariants enforced in code** (`verified` requires evidence; `passed` forbids
  regressions / unverified ACs) — a malformed report cannot be constructed.
- **Jira:** read-only httpx client + labelled fixtures (offline/CI).
- **Drift:** structural detector (critical/high/medium/low/none), `critical|high` blocks.
- **Acceptance logic:** per-AC verdict from evidence, regression detection (AC11/12/13).
- **CLI (Typer):** `auth jira`, `status`, `prepare`, `story`, `check-drift`,
  `accept-drift`, plus the Azure-Functions worker guard (`_check_worker`).

**Next (Phase 3–5):** the four verification layers (`verify`/`gate`) wiring
ruff/mypy/import-linter + scope + a **behave** behaviour suite driving MAF agents
(with `LocalEvaluator` tool-call checks as evidence), the Claude/Copilot adapters,
and CI. Blocked on the MAF rc1 API verification checklist (plan §9).

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
