"""Runs the deterministic Quality gates configured in .harness/config.yaml.

Each gate is a shell command; exit 0 = pass. Output is captured so the report can
show pass/fail without the agent re-interpreting raw logs.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GateResult:
    name: str
    command: str
    exit_code: int
    passed: bool
    output: str


@dataclass
class QualityResult:
    passed: bool
    results: list[GateResult]


def run_quality_gates(cfg: dict, root: Path | None = None) -> QualityResult:
    root = root or Path.cwd()
    results: list[GateResult] = []
    for cmd in cfg.get("quality", {}).get("commands", []):
        r = subprocess.run(cmd["run"], shell=True, cwd=root, capture_output=True, text=True)
        results.append(
            GateResult(
                name=cmd["name"],
                command=cmd["run"],
                exit_code=r.returncode,
                passed=r.returncode == 0,
                output=f"{r.stdout}{r.stderr}".strip(),
            )
        )
    return QualityResult(passed=all(r.passed for r in results), results=results)
