"""PII masking — a service utility. Imports only models."""

from __future__ import annotations

import re

_IBAN = re.compile(r"\b([A-Z]{2}\d{2})[A-Z0-9]{6,30}\b")


def mask_iban(text: str) -> str:
    """Mask all but the country+check digits of any IBAN in ``text``."""
    return _IBAN.sub(lambda m: f"{m.group(1)}****", text)
