"""TaskBoardProvider — the V2 abstraction that makes the AI reasoning layer
platform-independent. It only ever emits {task_id, action, confidence,
evidence}-shaped results; it never talks to Notion/Jira/the internal board
directly. Whatever provider a repo is configured to use is what actually
applies an approved suggestion.

Every provider must implement the minimum needed to close the human-
approval loop: find a task, read it, change its status, leave a comment.
create_task/list_tasks are optional — a provider that can't/shouldn't
support them (e.g. read-only integrations) raises NotImplementedError with
a clear message instead of being forced to fake support.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TaskBoardTask:
    """Provider-agnostic task representation. `id` is whatever the
    provider's own identifier is (a SprintSync Task UUID, a Notion page id,
    a Jira issue key, ...) — never assumed to be a UUID."""
    id: str
    title: str
    status: Optional[str] = None
    url: Optional[str] = None
    raw: dict = field(default_factory=dict)


class TaskBoardProvider(ABC):
    @abstractmethod
    async def find_task(self, query: str) -> Optional[TaskBoardTask]:
        """Best-effort search for one task matching a free-text query
        (usually a task title). Returns the single best match, or None."""

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[TaskBoardTask]:
        """Fetch one task by its provider-native id."""

    @abstractmethod
    async def update_status(self, task_id: str, status: str) -> TaskBoardTask:
        """Apply an already-human-approved status change. Never called
        without prior approval — see suggestions.py's approve_suggestion."""

    @abstractmethod
    async def add_comment(self, task_id: str, comment: str) -> None:
        """Leave a note on the task (e.g. why SprintSync changed its status)."""

    async def create_task(self, title: str, description: str = "") -> TaskBoardTask:
        raise NotImplementedError(f"{type(self).__name__} does not support creating tasks")

    async def list_tasks(self) -> List[TaskBoardTask]:
        raise NotImplementedError(f"{type(self).__name__} does not support listing tasks")

    async def close(self) -> None:
        """Providers holding an HTTP client override this; default is a no-op."""
        return None
