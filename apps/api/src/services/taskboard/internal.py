"""InternalBoardProvider — the existing Postgres Task table, wrapped as a
TaskBoardProvider. This is what makes the abstraction real rather than
cosmetic: V1's entire behavior (tasks live in this app's own DB) is just
the default provider, not a special case the reasoning/matching layers
know about.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity_log import ActivityLog, ActivityType
from src.models.task import Task, TaskStatus
from src.services import task_matching
from src.services.taskboard.base import TaskBoardProvider, TaskBoardTask


class InternalBoardProvider(TaskBoardProvider):
    def __init__(self, db: AsyncSession, repository_id: uuid.UUID):
        self.db = db
        self.repository_id = repository_id

    async def find_task(self, query: str) -> Optional[TaskBoardTask]:
        tasks = await self._list_task_rows()
        matches = task_matching.score_tasks(
            [query], [{"id": str(t.id), "title": t.title, "status": t.status.value} for t in tasks]
        )
        if not matches:
            return None
        best = matches[0]
        return next((self._to_board_task(t) for t in tasks if str(t.id) == best.task_id), None)

    async def get_task(self, task_id: str) -> Optional[TaskBoardTask]:
        result = await self.db.execute(
            select(Task).where(Task.id == uuid.UUID(task_id), Task.repository_id == self.repository_id)
        )
        task = result.scalar_one_or_none()
        return self._to_board_task(task) if task else None

    async def update_status(self, task_id: str, status: str) -> TaskBoardTask:
        result = await self.db.execute(
            select(Task).where(Task.id == uuid.UUID(task_id), Task.repository_id == self.repository_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found in repository {self.repository_id}")
        task.status = TaskStatus(status)
        await self.db.flush()
        return self._to_board_task(task)

    async def add_comment(self, task_id: str, comment: str) -> None:
        # No dedicated Comment model exists yet — recorded on the existing
        # audit trail (ActivityLog), which is also what the Activity page
        # already renders, so a "comment" shows up there for free.
        self.db.add(ActivityLog(
            repository_id=self.repository_id,
            event_type=ActivityType.TASK_UPDATED,
            title="SprintSync note added to task",
            description=comment,
            event_metadata={"task_id": task_id},
        ))
        await self.db.flush()

    async def create_task(self, title: str, description: str = "") -> TaskBoardTask:
        task = Task(repository_id=self.repository_id, title=title, description=description or None)
        self.db.add(task)
        await self.db.flush()
        return self._to_board_task(task)

    async def list_tasks(self) -> List[TaskBoardTask]:
        tasks = await self._list_task_rows()
        return [self._to_board_task(t) for t in tasks]

    async def _list_task_rows(self) -> List[Task]:
        """Real ORM rows, for this provider's own internal use (find_task's
        scoring needs the full row, not the trimmed TaskBoardTask shape).
        Never exposed outside this class — list_tasks() above is the public,
        interface-honoring surface."""
        result = await self.db.execute(
            select(Task).where(Task.repository_id == self.repository_id, Task.parent_id.is_(None))
        )
        return list(result.scalars().all())

    @staticmethod
    def _to_board_task(task: Task) -> TaskBoardTask:
        return TaskBoardTask(id=str(task.id), title=task.title, status=task.status.value)
