"""Agent-independent harness CLI (Typer). Claude Code, GitHub Copilot and CI all
drive the harness through this one entry point.

Phase 1+2 commands implemented here: auth, status, prepare, story, check-drift,
accept-drift, plus the Azure-Functions worker guard (_check_worker). The four
verification layers (verify/gate) arrive in Phase 3+.

Every command supports --format human | json | agent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer

from .acceptance_verifier import render_table, verify_acceptance
from .baseline import (
    HARNESS_VERSION,
    load_baseline,
    log_drift_accept,
    make_baseline,
    now_iso,
    save_baseline,
)
from .behaviour import run_suite
from .branch import current_git_branch, detect_ticket
from .config import load_config, repo_root
from .context import render_story_context
from .credentials import resolve_token, store_token
from .drift_detector import detect_drift
from .exit_codes import Exit
from .git_analyzer import base_commit, head_commit
from .jira_client import fetch_issue
from .report_builder import build_change_summary, build_final_report, check_scope_layer
from .story_normalizer import normalize_story
from .test_runner import run_quality_gates

app = typer.Typer(add_completion=False, help="Agent-independent feature harness (Python + MAF).")
auth_app = typer.Typer(help="Credential management (token stored in the OS keychain).")
app.add_typer(auth_app, name="auth")

ROOT = repo_root()


def _emit(fmt: str, human: str, data: dict[str, Any]) -> None:
    if fmt == "json":
        typer.echo(json.dumps(data, indent=2, default=str))
    elif fmt == "agent":
        typer.echo(data.get("agent", human))
    else:
        typer.echo(human)


def _fail(fmt: str, message: str, code: Exit, **extra: Any) -> None:
    _emit(fmt, message, {"ok": False, "error": message, **extra})
    raise typer.Exit(int(code))


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _cfg(fmt: str) -> dict:
    try:
        return load_config(ROOT)
    except Exception as e:  # noqa: BLE001
        _fail(fmt, f"Config error: {e}", Exit.WARNING)
        raise  # unreachable


def _require_ticket(cfg: dict, fmt: str) -> str:
    res = detect_ticket(cfg["branch"]["pattern"])
    if not res.ok:
        _fail(
            fmt, f"Invalid branch: {res.reason}", res.code or Exit.INVALID_BRANCH, reason=res.reason
        )
    return res.ticket  # type: ignore[return-value]


def _load_story(cfg: dict, ticket: str, fmt: str):
    fetched = fetch_issue(ticket, cfg, ROOT)
    if not fetched.ok:
        _fail(
            fmt,
            f"Jira error: {fetched.reason}",
            fetched.code or Exit.JIRA_OR_AUTH,
            reason=fetched.reason,
        )
    return normalize_story(fetched.issue, cfg), fetched.source  # type: ignore[arg-type]


def _blocked_banner(ticket: str, drift) -> str:
    changes = "\n".join(
        f'- {c.field}{" " + c.id if c.id else ""} {c.type}:\n  "{c.detail}"' for c in drift.changes
    )
    return (
        f"Story: {ticket}\nDrift: {drift.level}\n\nChanges:\n{changes}\n\nResult:\nBLOCKED\n\n"
        f"The Jira story changed after the local baseline was created.\n"
        f"Review and explicitly accept the new baseline "
        f"(`harness accept-drift {ticket}`) before continuing."
    )


def _write_runtime(name: str, content: str) -> Path:
    path = ROOT / ".harness" / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@auth_app.command("jira")
def auth_jira(fmt: str = typer.Option("human", "--format")) -> None:
    """Store the Jira token in the OS keychain (reads the token from stdin)."""
    cfg = _cfg(fmt)
    token = "" if sys.stdin.isatty() else sys.stdin.read().strip()
    if not token:
        _fail(
            fmt,
            'No token on stdin. Pipe it: `printf %s "$TOKEN" | harness auth jira`',
            Exit.JIRA_OR_AUTH,
        )
    store_token(cfg, token)
    _emit(
        fmt, "Jira token stored in the OS keychain. It is never written to the repo.", {"ok": True}
    )


@app.command()
def status(fmt: str = typer.Option("human", "--format")) -> None:
    """Show harness / baseline / branch state."""
    cfg = _cfg(fmt)
    branch = current_git_branch()
    det = detect_ticket(cfg["branch"]["pattern"])
    tok = resolve_token(cfg)
    ticket = det.ticket if det.ok else None
    baseline = load_baseline(ticket, ROOT) if ticket else None
    fixture_mode = cfg["jira"].get("fixture_mode") is True or not tok.token
    data = {
        "ok": det.ok,
        "branch": branch,
        "ticket": ticket,
        "credentials": f"resolved ({tok.source})" if tok.token else "none (fixture mode)",
        "fixtureMode": fixture_mode,
        "baseline": "present" if baseline else "absent",
        "harnessVersion": HARNESS_VERSION,
    }
    human = "\n".join(
        [
            f"Branch:       {branch or '(no git)'}",
            f"Ticket:       {ticket or '(invalid branch)'}",
            f"Credentials:  {data['credentials']}",
            f"Fixture mode: {fixture_mode}",
            f"Baseline:     {data['baseline']}",
            f"Harness:      v{HARNESS_VERSION}",
        ]
    )
    _emit(fmt, human, data)


@app.command()
def prepare(fmt: str = typer.Option("human", "--format")) -> None:
    """Load the story, compare to the baseline, write the agent context."""
    cfg = _cfg(fmt)
    branch = current_git_branch()
    ticket = _require_ticket(cfg, fmt)
    story, source = _load_story(cfg, ticket, fmt)

    from .git_analyzer import head_commit

    existing = load_baseline(ticket, ROOT)
    drift = None
    if existing is None:
        save_baseline(make_baseline(story, branch or "", head_commit(), source), ROOT)  # type: ignore[arg-type]
    else:
        drift = detect_drift(existing.story, story, cfg)

    ctx = render_story_context(
        story, source or "unknown", branch or "", drift, existing is not None
    )
    ctx_path = _write_runtime("current-story.md", ctx)

    blocking = bool(drift and drift.blocking)
    data = {
        "ok": not blocking,
        "ticket": ticket,
        "source": source,
        "branch": branch,
        "baseline": "found" if existing else "created",
        "drift": {
            "level": drift.level if drift else "none",
            "blocking": blocking,
            "changes": [c.__dict__ for c in drift.changes] if drift else [],
        },
        "contextPath": _rel(ctx_path),
        "agent": ctx,
    }
    if blocking:
        _emit(fmt, f"{_blocked_banner(ticket, drift)}\n\nContext written to {_rel(ctx_path)}", data)
        raise typer.Exit(int(Exit.DRIFT))
    human = (
        f"Prepared {ticket} ({source}). Baseline {'found' if existing else 'created'}. "
        f"Drift: {drift.level if drift else 'none'}. Context -> {_rel(ctx_path)}"
    )
    _emit(fmt, human, data)


@app.command()
def story(fmt: str = typer.Option("human", "--format")) -> None:
    """Print the normalised story."""
    cfg = _cfg(fmt)
    ticket = _require_ticket(cfg, fmt)
    st, source = _load_story(cfg, ticket, fmt)
    js = st.model_dump_json(by_alias=True, indent=2)
    _emit(fmt, js, {"ok": True, "source": source, "story": json.loads(js), "agent": js})


@app.command("check-drift")
def check_drift(fmt: str = typer.Option("human", "--format")) -> None:
    """Compare the current Jira story to the baseline."""
    cfg = _cfg(fmt)
    ticket = _require_ticket(cfg, fmt)
    existing = load_baseline(ticket, ROOT)
    if existing is None:
        _fail(fmt, f"No baseline for {ticket}. Run `harness prepare` first.", Exit.WARNING)
    st, _ = _load_story(cfg, ticket, fmt)
    drift = detect_drift(existing.story, st, cfg)  # type: ignore[union-attr]
    data = {
        "ok": not drift.blocking,
        "ticket": ticket,
        "level": drift.level,
        "blocking": drift.blocking,
        "changes": [c.__dict__ for c in drift.changes],
    }
    if drift.blocking:
        banner = _blocked_banner(ticket, drift)
        _emit(fmt, banner, {**data, "agent": banner})
        raise typer.Exit(int(Exit.DRIFT))
    human = (
        "Drift: none"
        if not drift.changes
        else f"Drift: {drift.level} (non-blocking)\n"
        + "\n".join(f"- {c.field} {c.type}: {c.detail}" for c in drift.changes)
    )
    _emit(fmt, human, {**data, "agent": human})
    raise typer.Exit(int(Exit.OK if drift.level == "none" else Exit.WARNING))


@app.command("accept-drift")
def accept_drift(
    ticket: str = typer.Argument(...), fmt: str = typer.Option("human", "--format")
) -> None:
    """Explicitly re-accept the baseline for TICKET (logged)."""
    cfg = _cfg(fmt)
    st, source = _load_story(cfg, ticket, fmt)
    branch = current_git_branch()
    from .git_analyzer import head_commit

    commit = head_commit()
    save_baseline(make_baseline(st, branch or "", commit, source), ROOT)  # type: ignore[arg-type]
    line = (
        f"{now_iso()} accept-drift {ticket} branch={branch} commit={commit or '-'} source={source}"
    )
    log_path = log_drift_accept(ROOT, line)
    _emit(
        fmt,
        f"Baseline for {ticket} re-accepted and logged -> {_rel(log_path)}",
        {"ok": True, "ticket": ticket},
    )


# Scaffold source (inside the installed package) -> destination in the consumer repo.
_SCAFFOLD = [
    ("config.yaml", ".harness/config.yaml"),
    ("importlinter.ini", ".importlinter"),
    ("AGENTS.md", "AGENTS.md"),
    ("CLAUDE.md", "CLAUDE.md"),
    ("github/copilot-instructions.md", ".github/copilot-instructions.md"),
    ("github/workflows/harness.yml", ".github/workflows/harness.yml"),
    ("claude/settings.json", ".claude/settings.json"),
    ("claude/hooks/session_prepare.py", ".claude/hooks/session_prepare.py"),
    ("claude/hooks/scope_guard.py", ".claude/hooks/scope_guard.py"),
    ("claude/hooks/read_guard.py", ".claude/hooks/read_guard.py"),
    ("claude/hooks/quality_hook.py", ".claude/hooks/quality_hook.py"),
    ("claude/agents/acceptance-reviewer.md", ".claude/agents/acceptance-reviewer.md"),
    ("claude/agents/change-summarizer.md", ".claude/agents/change-summarizer.md"),
    ("features/EXAMPLE.feature", "features/EXAMPLE.feature"),
    ("features/steps/example_steps.py", "features/steps/example_steps.py"),
]


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
    fmt: str = typer.Option("human", "--format"),
) -> None:
    """Scaffold the harness config, adapters, hooks and CI into THIS repo.

    Run once per agent repo after `pip install feature-harness`. Existing files are
    skipped unless --force. Then tailor `.harness/config.yaml` and `.importlinter`
    to your packages, and add `.harness/baseline/ runtime/ reports/` to .gitignore.
    """
    from importlib.resources import files

    scaffold_root = files("harness").joinpath("scaffold")
    written, skipped = [], []
    for src_rel, dest_rel in _SCAFFOLD:
        dest = ROOT / dest_rel
        if dest.exists() and not force:
            skipped.append(dest_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(scaffold_root.joinpath(src_rel).read_bytes())
        written.append(dest_rel)

    human = (
        "Scaffolded the harness into this repo.\n"
        + "\n".join(f"  + {w}" for w in written)
        + (f"\n  skipped (exists): {', '.join(skipped)}" if skipped else "")
        + "\n\nNext:\n"
        "  1. Tailor .harness/config.yaml (jira, scope) and .importlinter to your packages.\n"
        "  2. Add .harness/baseline/ .harness/runtime/ .harness/reports/ to .gitignore.\n"
        "  3. Write features/<KEY>.feature per story; delete features/EXAMPLE.*.\n"
        "  4. Run `harness status` then `harness prepare`."
    )
    _emit(fmt, human, {"ok": True, "written": written, "skipped": skipped})


def _run_behaviour_layer(cfg: dict, ticket: str, fmt: str):
    """Layer 3: run the behaviour suite and the acceptance worker against the
    baseline story (the agreed contract). Returns the validated report + its path."""
    existing = load_baseline(ticket, ROOT)
    if existing is not None:
        story_obj, source = existing.story, existing.source
    else:
        story_obj, source = _load_story(cfg, ticket, fmt)
    scenarios = run_suite(cfg, ROOT)
    report = verify_acceptance(
        story_obj,
        scenarios,
        source=source or "unknown",
        base_commit=base_commit().commit,
        head_commit=head_commit(),
    )
    report_path = ROOT / ".harness" / "reports" / f"{ticket}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_json() + "\n")
    return report, report_path


@app.command()
def summarize(fmt: str = typer.Option("human", "--format")) -> None:
    """Read-only change summary (WHAT changed / files / anything surprising)."""
    cfg = _cfg(fmt)
    summary = build_change_summary(cfg, ROOT)
    _emit(fmt, summary["text"], {"ok": True, "files": summary["files"], "agent": summary["text"]})


@app.command()
def verify(fmt: str = typer.Option("human", "--format")) -> None:
    """Run all four layers (Quality, Scope, Behaviour, Reporting) — always all four."""
    cfg = _cfg(fmt)
    ticket = _require_ticket(cfg, fmt)

    quality = run_quality_gates(cfg, ROOT)
    scope = check_scope_layer(cfg, ROOT)
    report, report_path = _run_behaviour_layer(cfg, ticket, fmt)
    final = build_final_report(quality, scope, report)

    data = {
        "ok": final.green,
        "ticket": ticket,
        "layers": {
            "quality": {
                "passed": quality.passed,
                "results": [{"name": r.name, "exitCode": r.exit_code} for r in quality.results],
            },
            "scope": {"passed": scope.passed, "violations": scope.violations},
            "behaviour": {
                "passed": report.overall_status == "passed",
                "report": report.model_dump(by_alias=True),
                "reportPath": _rel(report_path),
            },
        },
        "overall": "GREEN" if final.green else "RED",
        "failing": final.failing,
        "agent": f"{final.text}\n\n{render_table(report)}",
    }
    _emit(fmt, final.text, data)
    raise typer.Exit(int(Exit.OK if final.green else Exit.VERIFY_FAILED))


@app.command()
def gate(fmt: str = typer.Option("human", "--format")) -> None:
    """Drift gate + verify -> one GREEN/RED verdict for commit/PR."""
    cfg = _cfg(fmt)
    ticket = _require_ticket(cfg, fmt)

    existing = load_baseline(ticket, ROOT)
    drift = None
    if existing is not None:
        st, _ = _load_story(cfg, ticket, fmt)
        drift = detect_drift(existing.story, st, cfg)
    if drift and drift.blocking:
        banner = _blocked_banner(ticket, drift)
        _emit(
            fmt,
            banner,
            {"ok": False, "ticket": ticket, "stage": "drift", "overall": "RED", "agent": banner},
        )
        raise typer.Exit(int(Exit.DRIFT))

    quality = run_quality_gates(cfg, ROOT)
    scope = check_scope_layer(cfg, ROOT)
    report, report_path = _run_behaviour_layer(cfg, ticket, fmt)
    final = build_final_report(quality, scope, report)

    if not drift or drift.level == "none":
        drift_state = "✓ none"
    else:
        drift_state = f"~ {drift.level} (non-blocking)"
    text = f"Drift:     {drift_state}\n{final.text}"
    data = {
        "ok": final.green,
        "ticket": ticket,
        "drift": {"level": drift.level if drift else "none"},
        "overall": "GREEN" if final.green else "RED",
        "failing": final.failing,
        "reportPath": _rel(report_path),
        "agent": f"{text}\n\n{render_table(report)}",
    }
    _emit(fmt, text, data)
    raise typer.Exit(int(Exit.OK if final.green else Exit.VERIFY_FAILED))


@app.command()
def report(fmt: str = typer.Option("human", "--format")) -> None:
    """Print the last machine-readable acceptance report."""
    cfg = _cfg(fmt)
    ticket = _require_ticket(cfg, fmt)
    path = ROOT / ".harness" / "reports" / f"{ticket}.json"
    if not path.exists():
        _fail(fmt, f"No report for {ticket}. Run `harness verify` first.", Exit.WARNING)
    from .models import AcceptanceReport

    rep = AcceptanceReport.model_validate_json(path.read_text())
    _emit(
        fmt,
        render_table(rep),
        {
            "ok": rep.overall_status == "passed",
            "report": rep.model_dump(by_alias=True),
            "agent": rep.to_json(),
        },
    )


@app.command("_check_worker", hidden=True)
def check_worker(fmt: str = typer.Option("human", "--format")) -> None:
    """Azure Functions guard: azure-functions-worker must NOT be pinned in requirements.txt."""
    req = ROOT / "requirements.txt"
    if req.exists():
        for line in req.read_text().splitlines():
            name = line.strip().lower().split("==")[0].split(">=")[0].split("<")[0].strip()
            if name == "azure-functions-worker":
                typer.echo(
                    "requirements.txt pins azure-functions-worker — "
                    "the Functions host manages it; remove it.",
                    err=True,
                )
                raise typer.Exit(1)
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
