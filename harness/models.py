"""Pydantic v2 models for the story, baseline and acceptance report.

The report INVARIANTS from the spec are enforced here in code (``@model_validator``),
so a malformed report can never be constructed:

  - ``verified`` requires at least one evidence entry.
  - ``not_verified`` requires at least one gap/reason.
  - ``overallStatus == "passed"`` requires every AC verified and zero regressions.

Field aliases keep the serialised JSON camelCase, byte-compatible with the Node
harness report (acceptanceCriteria, overallStatus, baseCommit, ...).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TICKET_PATTERN = r"^[A-Z][A-Z0-9]+-\d+$"

_camel = ConfigDict(populate_by_name=True)


class AcceptanceCriterion(BaseModel):
    model_config = _camel
    id: str
    text: str


class NormalizedStory(BaseModel):
    model_config = _camel
    key: str = Field(pattern=TICKET_PATTERN)
    summary: str = ""
    description: str = ""
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list, alias="acceptanceCriteria"
    )
    status: str = ""
    priority: str = ""
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    updated: str = ""


class Baseline(BaseModel):
    model_config = _camel
    story: NormalizedStory
    jira_updated: str = Field(alias="jiraUpdated", default="")
    created_at: str = Field(alias="createdAt")
    git_commit: str | None = Field(alias="gitCommit", default=None)
    branch: str
    harness_version: str = Field(alias="harnessVersion")
    source: Literal["jira", "fixture"]


class Evidence(BaseModel):
    model_config = _camel
    type: Literal["scenario", "test", "codepath", "manual", "eval", "trace"]
    name: str = ""
    result: Literal["passed", "failed", "pending"]


Verdict = Literal["pass", "FAIL", "unclear", "blocked"]
Status = Literal["verified", "not_verified", "blocked"]


class Criterion(BaseModel):
    model_config = _camel
    id: str
    text: str
    status: Status
    verdict: Verdict
    evidence: list[Evidence] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _invariants(self) -> Criterion:
        if self.status == "verified" and not self.evidence:
            raise ValueError(f'{self.id}: status "verified" requires at least one evidence entry')
        if self.status == "not_verified" and not self.gaps:
            raise ValueError(f'{self.id}: status "not_verified" requires a gap/reason')
        return self


class Regression(BaseModel):
    model_config = _camel
    story: str
    name: str
    result: str = "failed"
    ac: str | None = None


class AcceptanceReport(BaseModel):
    model_config = _camel
    ticket: str = Field(pattern=TICKET_PATTERN)
    source: Literal["jira", "fixture", "unknown"] = "unknown"
    base_commit: str | None = Field(alias="baseCommit", default=None)
    head_commit: str | None = Field(alias="headCommit", default=None)
    criteria: list[Criterion] = Field(default_factory=list)
    regressions: list[Regression] = Field(default_factory=list)
    overall_status: Literal["passed", "failed"] = Field(alias="overallStatus")

    @model_validator(mode="after")
    def _overall_invariants(self) -> AcceptanceReport:
        if self.overall_status == "passed":
            if not self.criteria or not all(c.status == "verified" for c in self.criteria):
                raise ValueError('overallStatus "passed" requires every AC verified')
            if self.regressions:
                raise ValueError('overallStatus "passed" forbids any regression')
        return self

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, indent=2)
