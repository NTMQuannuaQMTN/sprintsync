"""Configurable event -> task-status mapping (V2 Phase 6).

A repo's status_mapping (JSONB column) overrides individual keys of
DEFAULT_STATUS_MAPPING — an unset repo never needs every key defined, and a
key this app doesn't recognize in a user's config is ignored rather than
crashing anything. This never mutates a Task directly: it only decides what
status a Suggestion *proposes*; the human-approval gate (unchanged from V1)
is what actually applies it. That's what "do not destroy or overwrite
user-defined workflows" means in practice here — the mapping only ever
proposes, and a human can always reject a proposal that doesn't fit how
their project actually works.
"""
from typing import Optional

from src.models.task import TaskStatus

# Event keys, matching the shape used across webhook.py / commits.py.
EventKey = str  # "push" | "pr_opened" | "pr_synchronize" | "pr_merged" | "pr_closed"

DEFAULT_STATUS_MAPPING: dict[EventKey, str] = {
    "push": TaskStatus.IN_PROGRESS.value,
    "pr_opened": TaskStatus.IN_PROGRESS.value,
    "pr_synchronize": TaskStatus.IN_PROGRESS.value,
    "pr_merged": TaskStatus.DONE.value,
    "pr_closed": TaskStatus.BLOCKED.value,  # closed without merging — worth a human look, not silently "done"
}

_VALID_STATUSES = {s.value for s in TaskStatus}


def resolve_status(event_key: EventKey, repo_status_mapping: Optional[dict]) -> str:
    """The status a Suggestion should *propose* for this event, honoring a
    repo's override where it supplies one and is actually a valid status."""
    if repo_status_mapping:
        override = repo_status_mapping.get(event_key)
        if override in _VALID_STATUSES:
            return override
    return DEFAULT_STATUS_MAPPING.get(event_key, TaskStatus.IN_PROGRESS.value)
