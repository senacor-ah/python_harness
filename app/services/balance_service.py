"""Balance service — the SERVICE layer. Imports only models.

Stands in for the real mTLS call to the account backend (services/api/*). Kept as
plain in-memory data so behaviour scenarios run offline and deterministically.
"""

from __future__ import annotations

from app.models.core import Account

_ACCOUNTS = {
    "ACC-1": Account(account_id="ACC-1", iban="DE89370400440532013000", balance_cents=125_00),
}


def get_account(account_id: str) -> Account | None:
    return _ACCOUNTS.get(account_id)
