"""Secret handling for the Jira token. The token is NEVER stored in the repo and
NEVER printed. Resolution order (first hit wins):

  1. token_command  — a shell command that PRINTS the token (secret manager)
  2. OS keychain    — via ``keyring`` (macOS Keychain, Windows Credential Manager,
                      Linux libsecret)
  3. env var        — JIRA_API_TOKEN (also how CI injects its secret)

The env var is checked BEFORE the keychain so CI (which has no keychain backend)
never touches one. The model/agent only ever calls ``harness prepare``; it never
sees the token.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import keyring


def mask(value: str | None) -> str:
    return "***REDACTED***" if value else ""


def resolve_email(cfg: dict) -> str:
    env = cfg.get("credentials", {}).get("email_env", "JIRA_EMAIL")
    return os.environ.get(env, "")


@dataclass
class TokenResult:
    token: str | None
    source: str | None  # non-secret label: "token_command" | "env" | "keychain" | None


def resolve_token(cfg: dict) -> TokenResult:
    c = cfg.get("credentials", {})

    cmd = (c.get("token_command") or "").strip()
    if cmd:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return TokenResult(r.stdout.strip(), "token_command")

    # Env first — CI-safe (no keychain backend in CI).
    token_env = c.get("token_env", "JIRA_API_TOKEN")
    if os.environ.get(token_env):
        return TokenResult(os.environ[token_env], "env")

    service = c.get("service", "harness-jira")
    username = resolve_email(cfg) or "jira"
    try:
        stored = keyring.get_password(service, username)
    except Exception:
        stored = None
    if stored:
        return TokenResult(stored, "keychain")

    return TokenResult(None, None)


def store_token(cfg: dict, token: str) -> None:
    """Store the token in the OS keychain (used by ``harness auth jira``)."""
    c = cfg.get("credentials", {})
    service = c.get("service", "harness-jira")
    username = resolve_email(cfg) or "jira"
    keyring.set_password(service, username, token)
