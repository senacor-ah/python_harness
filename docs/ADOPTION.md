# Adopting the harness in a MAF agent repo

The harness ships as **one shared, pip-installable package** (`python_harness`).
Each agent container repo installs it as a **dev dependency** and keeps only a small
`.harness/config.yaml` — the business logic (drift, scope, acceptance) lives in the
package, so you maintain it once for all agents.

> The harness is a **dev/CI tool**. It is NOT installed into the runtime container
> image — keep it in your dev/test extras only.

## 1. Install (per agent repo)

Publish the wheel to your internal index (or reference it as a git dependency),
then add it to your dev extras:

```toml
# pyproject.toml of the agent repo
[project.optional-dependencies]
dev = [
    "python_harness>=1.0",   # internal index, or:
    # "python_harness @ git+https://your.git/python_harness.git@v1.0.0",
    "ruff>=0.6", "mypy>=1.11", "import-linter>=2", "behave>=1.2.6",
    "pytest>=8",
]
```

```bash
pip install -e ".[dev]"      # or: pip install python_harness
```

## 2. Scaffold

```bash
python -m harness init       # writes config, adapters, hooks, CI, example feature
```

This creates `.harness/config.yaml`, `.importlinter`, `AGENTS.md`, `CLAUDE.md`,
`.github/copilot-instructions.md`, `.github/workflows/harness.yml`, `.claude/`
(settings + hooks + subagents), and `features/EXAMPLE.*`. Existing files are
skipped unless you pass `--force`.

## 3. Tailor to this agent (the only per-repo work)

1. **`.harness/config.yaml`**
   - `jira.base_url` and `acceptance_criteria_fields` (your custom field ids).
   - `scope.allowed` / `scope.denied` → your top-level packages. Freeze the
     sensitive surfaces: `auth/`, `services/api/**` (mTLS clients),
     `middleware/masking.py`, `prompts/safety-rules.md`, `function_app.py`.
   - `quality.commands` → point `mypy` at your packages.
2. **`.importlinter`** → your real layer packages (routes/workflows/agents/tools/
   services/models) or `root_package` if it's one package.
3. **`.claude/settings.json`** → mirror the `scope.allowed` paths in the `Edit(...)`
   permissions (defense in depth alongside the hooks).
4. **`.gitignore`** → add:
   ```
   .harness/baseline/
   .harness/runtime/
   .harness/reports/
   ```
5. Delete `features/EXAMPLE.*` and write one `features/<KEY>.feature` per story
   (tags `@story:<KEY>` and `@ac:<ACid>`), with steps that drive your MAF agent.

## 4. Credentials (never in the repo)

```bash
printf %s "$JIRA_TOKEN" | python -m harness auth jira   # stores in the OS keychain
export JIRA_EMAIL="you@org.com"
```

In CI, inject `JIRA_EMAIL` / `JIRA_API_TOKEN` as secrets (the workflow already reads
them). Fork PRs have no secrets → the harness falls back to fixture mode.

## 5. Daily flow

```bash
git switch -c feature/PROJ-1234
python -m harness prepare        # load story, baseline, write context (blocks on drift)
# ...implement inside the allowed scope, write/adjust features/PROJ-1234.feature...
python -m harness verify         # Quality + Scope + Behaviour + Reporting
python -m harness gate           # drift + verify → one GREEN/RED verdict for the PR
```

Claude Code picks up the hooks automatically; Copilot follows
`.github/copilot-instructions.md`; CI runs the same `harness gate`.

## 6. MAF evidence (Phase 4)

Back an acceptance criterion with a MAF `LocalEvaluator` check (deterministic,
offline) in a behave step — e.g. assert `tool_called_check("get_balance")` on a run
driven by a fake `ChatClientProtocol` stub. The report's `Evidence.type` already
accepts `eval` and `trace` (OTel spans), so no harness change is needed — only the
step wiring. Pin the exact MAF rc1 symbols first with `python -m harness`'s sibling
script `scripts/probe_maf.py` (see the port plan §9).

## Upgrading the harness

Bump the `python_harness` version in the agent repo's dev extras. Re-run
`harness init --force` only if you want the latest adapter/hook templates (it will
overwrite them; your `.harness/config.yaml` is yours to keep).
