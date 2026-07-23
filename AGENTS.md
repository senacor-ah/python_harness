# AGENTS.md

The single, **agent-independent** working agreement for this repository. Claude
Code, GitHub Copilot and CI all follow THIS file. It contains no tool-specific
detail — only what every agent must do, expressed as `harness` commands. The
business logic lives in one CLI (`python -m harness`); adapters never re-implement
drift, story, scope or acceptance logic.

## Golden rule

> Agent instructions improve behaviour, but they are **not** a security boundary.
> Enforcement lives in the deterministic hooks, the Git/scope checks and CI.

## Where stories live

User stories and epics live **only in Jira** — never committed. The harness pulls
the story for the current branch, stores a **local, git-ignored** baseline under
`.harness/`, and compares against it.

## Branch convention

`feature/<JIRA-KEY>`, e.g. `feature/PROJ-1234`.

## Before any code change

```text
1. Check the harness status.        python -m harness status
2. Load the story context.          python -m harness prepare --format agent
3. Check Jira drift.                (prepare/gate do this; or: check-drift)
4. If drift is BLOCKING, STOP.      exit code 3 → do not implement
5. Read the acceptance criteria.    (.harness/runtime/current-story.md)
6. Map your implementation to the criteria.
```

## After implementation

```text
1. Run the behaviour suite + checks. (verify runs them)
2. Run acceptance verification.      python -m harness verify --format agent
3. Report each criterion WITH evidence (a passing behaviour scenario / eval).
4. Never claim an AC is met without evidence.
5. Produce the GREEN/RED report.     python -m harness gate
```

## Hard rules

- No claim of a met acceptance criterion without concrete evidence (a green
  behaviour scenario, a MAF `LocalEvaluator` check, or a reproducible code path).
- Do not modify the baseline; a human runs `harness accept-drift <KEY>` explicitly.
- Do not edit outside the allowed scope (`.harness/config.yaml` → `scope.allowed`):
  the harness, `app/services/**` (mTLS clients, masking), auth and CI are off-limits.
- Do not read secret files. The Jira token lives in the OS keychain, never the repo.
- Do not bypass a blocking hook or drift.
- Never pin `azure-functions-worker` in `requirements.txt` (the Functions host owns it).

## Exit codes (stable)

| code | meaning |
| ---- | ------- |
| 0 | success |
| 2 | non-blocking warning (low/medium drift) |
| 3 | **blocking drift** |
| 4 | Jira / authentication error |
| 5 | invalid branch |
| 6 | verification failed (a layer is RED) |
