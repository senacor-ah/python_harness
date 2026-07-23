"""Render the agent-facing story context written to .harness/runtime/current-story.md."""

from __future__ import annotations

from .drift_detector import DriftResult
from .models import NormalizedStory


def render_story_context(
    story: NormalizedStory,
    source: str,
    branch: str,
    drift: DriftResult | None,
    baseline_exists: bool,
) -> str:
    acs = "\n\n".join(f"### {ac.id}\n\n{ac.text}" for ac in story.acceptance_criteria)
    if drift is None:
        drift_line = "Jira drift: baseline just created"
    else:
        drift_line = f"Jira drift: {drift.level}" + (" (BLOCKING)" if drift.blocking else "")
    source_note = (
        "\n> **Note:** story loaded from a FIXTURE stand-in, not live Jira.\n"
        if source == "fixture"
        else ""
    )
    return f"""# Feature {story.key}
{source_note}
## Summary

{story.summary or "(no summary)"}

## Acceptance Criteria

{acs or "(no acceptance criteria found)"}

## Scope

- Work only inside the configured allowed paths (see .harness/config.yaml).
- Do not edit auth, the mTLS service clients, masking, or the harness itself.

## Harness Status

- {"Baseline found" if baseline_exists else "Baseline created"}
- {drift_line}
- Current branch: {branch}
- Story source: {source}

## Agent Rules

- Do not claim an AC is complete without evidence (a passing behaviour scenario or MAF eval check).
- Do not modify the Jira baseline (use `harness accept-drift` explicitly if the story changed).
- Stay inside the configured repository scope.
- Run `harness verify` before declaring completion.
"""
