"""Run the cumulative behaviour suite with ``behave`` and map each scenario to a
framework-independent ``ScenarioResult`` (passed / failed / pending).

behave is chosen over pytest-bdd because it models the four Gherkin states natively:
an UNDEFINED step (a not-yet-implemented future story) is reported as ``undefined``,
distinct from a ``failed`` assertion. We fold ``undefined``/``skipped``/``untested``
into ``pending`` so the acceptance worker treats "not implemented" differently from
"implemented but wrong" (AC11/12/13).

Scenarios are tagged ``@story:<KEY>`` and ``@ac:<ACid>`` so results map to the right
story and AC; the suite always runs every feature file, so regressions surface.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .acceptance_verifier import ScenarioResult


def _tag_value(tags: list[str], name: str) -> str | None:
    # behave stores tags without the leading "@".
    prefix = f"{name}:"
    for t in tags:
        if t.startswith(prefix):
            return t[len(prefix) :]
    return None


def _scenario_status(element: dict) -> str:
    statuses = [(s.get("result") or {}).get("status", "skipped") for s in element.get("steps", [])]
    if "failed" in statuses:
        return "failed"
    if "undefined" in statuses:
        return "pending"
    if statuses and all(s == "passed" for s in statuses):
        return "passed"
    return "pending"  # skipped / untested / empty -> not implemented


def run_suite(cfg: dict, root: Path | None = None) -> list[ScenarioResult]:
    root = root or Path.cwd()
    features_dir = cfg.get("behaviour", {}).get("features_dir", "features")
    if not (root / features_dir).exists():
        return []

    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as tf:
        out_path = tf.name
    try:
        # Invoke behave as a module with the current interpreter so it is found in
        # whatever venv the harness runs under (no reliance on PATH).
        subprocess.run(
            [
                sys.executable, "-m", "behave", features_dir,
                "--format", "json", "--outfile", out_path,
                "--no-summary", "--no-snippets",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        raw = Path(out_path).read_text().strip()
    finally:
        Path(out_path).unlink(missing_ok=True)

    if not raw:
        return []
    features = json.loads(raw)

    results: list[ScenarioResult] = []
    for feature in features:
        feature_story = _tag_value(feature.get("tags", []), "story")
        for element in feature.get("elements", []):
            if element.get("type") != "scenario":
                continue
            tags = element.get("tags", [])
            status = _scenario_status(element)
            results.append(
                ScenarioResult(
                    story=_tag_value(tags, "story") or feature_story,
                    ac=_tag_value(tags, "ac"),
                    name=element.get("name", ""),
                    result=status,
                    error=None if status == "passed" else f"scenario {status}",
                )
            )
    return results
