"""Balance tool — the TOOL layer. Imports services + models, never agents/workflows.

In Phase 4 this function is registered with a MAF agent via ``@tool``; here it is a
plain function so it is testable in isolation and by behaviour scenarios.
"""

from __future__ import annotations

from app.models.core import User, can
from app.services.balance_service import get_account
from app.services.masking import mask_iban


def get_balance(user: User, account_id: str) -> dict:
    """AC1: authorized user gets the balance. AC2: the IBAN is masked in the output."""
    if not can(user, "invoice:read"):
        return {"status": 403, "error": "forbidden"}
    account = get_account(account_id)
    if account is None:
        return {"status": 404, "error": "not found"}
    euros = account.balance_cents / 100
    return {
        "status": 200,
        "iban": mask_iban(account.iban),
        "balance": f"{euros:.2f} EUR",
    }
