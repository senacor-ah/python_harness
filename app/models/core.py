"""Domain models — the LEAF layer. Imports nothing internal (pure data)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    scopes: set[str] = field(default_factory=set)


def can(user: User, scope: str) -> bool:
    return scope in user.scopes


@dataclass
class Account:
    account_id: str
    iban: str
    balance_cents: int
