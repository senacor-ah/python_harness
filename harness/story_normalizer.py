"""Turn a raw Jira issue (or fixture) into a STABLE normalised story.

Raw Jira content must never be compared directly: rich text (Atlassian Document
Format), unstable field ordering and presentation-only differences would create
false drift. Normalisation gives drift-detection a deterministic surface.
"""

from __future__ import annotations

import re
from typing import Any

from .models import AcceptanceCriterion, NormalizedStory


def adf_to_text(node: Any) -> str:
    """Convert Atlassian Document Format (or a plain string) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n) for n in node)
    if not isinstance(node, dict):
        return ""

    t = node.get("type")
    if t == "text":
        return node.get("text", "")
    if t == "hardBreak":
        return "\n"
    if t in ("paragraph", "heading"):
        return _block_text(node) + "\n"
    if t == "listItem":
        return _block_text(node)
    if t in ("bulletList", "orderedList"):
        return "\n".join(adf_to_text(li).strip() for li in node.get("content", [])) + "\n"
    return _block_text(node)


def _block_text(node: dict) -> str:
    return "".join(adf_to_text(c) for c in node.get("content", []))


def normalize_text(text: Any) -> str:
    """Collapse whitespace and drop presentation-only differences."""
    s = str(text or "").replace("\r\n", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    lines = [ln.strip() for ln in s.split("\n")]
    return "\n".join(ln for ln in lines if ln != "").strip()


def split_criteria(text: str) -> list[AcceptanceCriterion]:
    """Split criteria text into lines, drop bullet/enumeration prefixes, assign stable ids."""
    out: list[AcceptanceCriterion] = []
    for line in text.split("\n"):
        cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if cleaned:
            out.append(AcceptanceCriterion(id=f"AC{len(out) + 1}", text=cleaned))
    return out


def extract_acceptance_criteria(fields: dict, field_names: list[str]) -> list[AcceptanceCriterion]:
    for name in field_names:
        text = normalize_text(adf_to_text(fields.get(name)))
        if text:
            return split_criteria(text)
    return []


def normalize_story(issue: dict, cfg: dict) -> NormalizedStory:
    fields = issue.get("fields", {}) or {}
    ac_fields = cfg.get("jira", {}).get("acceptance_criteria_fields", ["description"])

    def _named(v: Any) -> str:
        if isinstance(v, dict):
            return str(v.get("name", ""))
        return str(v or "")

    components = sorted(_named(c) for c in (fields.get("components") or []))
    labels = sorted(str(x) for x in (fields.get("labels") or []))

    return NormalizedStory(
        key=issue["key"],
        summary=normalize_text(fields.get("summary", "")),
        description=normalize_text(adf_to_text(fields.get("description"))),
        acceptanceCriteria=extract_acceptance_criteria(fields, ac_fields),
        status=_named(fields.get("status")),
        priority=_named(fields.get("priority")),
        labels=labels,
        components=components,
        updated=fields.get("updated", "") or "",
    )
