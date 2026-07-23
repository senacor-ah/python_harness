"""Balance agent — the AGENT layer. Imports tools + models, never workflows/routes.

This is a STUB that mimics the MAF tool-calling loop deterministically: given a
user query it decides to call ``get_balance`` and records the tool call. In Phase 4
this is replaced by a real MAF ``ChatAgent`` (chat client + instructions + the
``get_balance`` tool); the recorded ``tool_calls`` become MAF ``LocalEvaluator``
``tool_called_check`` / ``tool_call_args_match`` evidence. The rest of the harness
does not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.core import User
from app.tools.balance_tool import get_balance


@dataclass
class AgentResult:
    text: str
    tool_calls: list[dict] = field(default_factory=list)


def run(user: User, query: str, account_id: str = "ACC-1") -> AgentResult:
    result = AgentResult(text="")
    if "kontostand" in query.lower() or "balance" in query.lower():
        out = get_balance(user, account_id)
        result.tool_calls.append({"name": "get_balance", "args": {"account_id": account_id}})
        if out["status"] == 200:
            result.text = f"Ihr Kontostand für {out['iban']} beträgt {out['balance']}."
        elif out["status"] == 403:
            result.text = "Zugriff verweigert (403)."
        else:
            result.text = "Konto nicht gefunden."
    else:
        result.text = "Ich kann bei Kontostandsabfragen helfen."
    return result
