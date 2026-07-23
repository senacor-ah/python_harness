"""Session/login service for the ALREADY-SHIPPED story PROJ-1000. Exists so the
cumulative behaviour suite can prove new work did not regress it.
"""

from __future__ import annotations

_SESSIONS: dict[str, str] = {}


def login(user_id: str, password: str) -> dict:
    if not user_id or not password:
        return {"ok": False, "status": 401}
    token = f"sess_{user_id}_{len(password)}"
    _SESSIONS[token] = user_id
    return {"ok": True, "status": 200, "token": token}
