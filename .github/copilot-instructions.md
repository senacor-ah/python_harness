# GitHub Copilot instructions

This repository uses a shared, **agent-independent** feature harness. The full
rules are in [`AGENTS.md`](../AGENTS.md) — read it. The essential commands are
repeated here explicitly, so functionality does not depend on whether the host
follows cross-references or runs a startup hook. Copilot works if it merely reads
these instructions and calls the CLI. Do not re-implement drift/story/scope/
acceptance logic in generated code — it lives in `python -m harness`.

## Stories live in Jira only

The harness pulls the story for the current `feature/<JIRA-KEY>` branch and keeps a
local, git-ignored baseline. Nothing about a story is committed.

## Before you change any code

```bash
python -m harness prepare --format agent
```

- Exit code `3` = **blocking Jira drift**: the story changed after the baseline.
  **Stop.** A human runs `python -m harness accept-drift <KEY>`.
- Exit `5` = not on a `feature/<JIRA-KEY>` branch.
- Story summary + acceptance criteria are written to `.harness/runtime/current-story.md`.

Map every change to a specific acceptance criterion.

## Before you finish / open a PR

```bash
python -m harness verify --format agent   # all four layers, per-AC evidence
python -m harness gate                     # drift + verify → GREEN/RED verdict
```

Report each acceptance criterion **with evidence** (a passing behaviour scenario).
`gate`/`verify` exit `0` only when GREEN; otherwise `6`.

## Hard rules

- Do not edit `harness/`, `.harness/config.yaml`, `app/services/**`, or `.github/`.
- Do not read secret files. The Jira token lives in the OS keychain
  (`python -m harness auth jira`), never in the repo.
- Never pin `azure-functions-worker` in `requirements.txt`.
