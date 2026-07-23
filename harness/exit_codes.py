"""Stable, documented exit codes shared by every harness command.

Agents and CI branch on these numbers, so they must never drift. Identical to the
Node harness contract.
"""

from enum import IntEnum


class Exit(IntEnum):
    OK = 0  # success
    WARNING = 2  # non-blocking warning (low/medium drift, missing fixture)
    DRIFT = 3  # blocking drift — baseline no longer matches Jira
    JIRA_OR_AUTH = 4  # Jira unreachable, unauthorized, or story not found
    INVALID_BRANCH = 5  # not a git repo, detached HEAD, or bad branch format
    VERIFY_FAILED = 6  # a verification layer failed
