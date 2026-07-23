"""Read-only Jira client. ONLY performs GET requests — the harness never writes to
Jira. When credentials are absent or ``fixture_mode`` is on, it reads a clearly-
labelled fixture that STANDS IN for the Jira REST response (offline dev, CI, tests).
A fixture result carries ``source == "fixture"`` and is never presented as real proof.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from .credentials import resolve_email, resolve_token
from .exit_codes import Exit


@dataclass
class FetchResult:
    ok: bool
    source: str | None = None
    issue: dict | None = None
    code: Exit | None = None
    reason: str | None = None


def fetch_issue(key: str, cfg: dict, root: Path | None = None) -> FetchResult:
    root = root or Path.cwd()
    token = resolve_token(cfg).token
    use_fixture = cfg.get("jira", {}).get("fixture_mode") is True or not token
    if use_fixture:
        return _read_fixture(key, cfg, root)
    return _fetch_network(key, cfg, token)


def _read_fixture(key: str, cfg: dict, root: Path) -> FetchResult:
    fixtures_dir = cfg.get("jira", {}).get("fixtures_dir", ".harness/fixtures")
    path = root / fixtures_dir / f"{key}.json"
    if not path.exists():
        return FetchResult(
            ok=False,
            code=Exit.JIRA_OR_AUTH,
            reason=f"no fixture for {key} at {path} (fixture mode is on)",
        )
    return FetchResult(ok=True, source="fixture", issue=json.loads(path.read_text()))


def _fetch_network(key: str, cfg: dict, token: str) -> FetchResult:
    import httpx  # local import so offline/fixture use needs no network stack

    base = (cfg.get("jira", {}).get("base_url") or "").rstrip("/")
    if not base:
        return FetchResult(ok=False, code=Exit.JIRA_OR_AUTH, reason="jira.base_url not configured")
    email = resolve_email(cfg)
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    url = f"{base}/rest/api/3/issue/{key}"
    try:
        res = httpx.get(
            url,
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
            timeout=15,
        )
    except httpx.HTTPError:
        return FetchResult(ok=False, code=Exit.JIRA_OR_AUTH, reason=f"Jira unreachable at {base}")

    if res.status_code in (401, 403):
        return FetchResult(
            ok=False, code=Exit.JIRA_OR_AUTH, reason="Jira rejected credentials (401/403)"
        )
    if res.status_code == 404:
        return FetchResult(
            ok=False, code=Exit.JIRA_OR_AUTH, reason=f"Jira story {key} not found (404)"
        )
    if res.status_code >= 400:
        return FetchResult(
            ok=False, code=Exit.JIRA_OR_AUTH, reason=f"Jira returned HTTP {res.status_code}"
        )
    return FetchResult(ok=True, source="jira", issue=res.json())
