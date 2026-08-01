"""Task CRUD endpoints."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.models.task import Task, TaskStatus
from src.models.project_spec import ProjectSpecification
from src.models.activity_log import ActivityLog, ActivityType
from src.schemas.task import TaskCreate, TaskUpdate, TaskOut, TaskBulkCreate

router = APIRouter(prefix="/repositories/{repo_id}/tasks", tags=["tasks"])


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=List[TaskOut])
async def list_tasks(
    repo_id: uuid.UUID,
    status: Optional[TaskStatus] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)

    q = select(Task).where(Task.repository_id == repo_id, Task.parent_id.is_(None))
    if status:
        q = q.where(Task.status == status)
    q = q.order_by(Task.order_index, Task.created_at)

    result = await db.execute(q)
    tasks = result.scalars().all()

    # Load subtasks for each root task
    out = []
    for task in tasks:
        sub_result = await db.execute(
            select(Task).where(Task.parent_id == task.id).order_by(Task.order_index)
        )
        subtasks = sub_result.scalars().all()
        task_out = TaskOut.model_validate(task)
        task_out.subtasks = [TaskOut.model_validate(s) for s in subtasks]
        out.append(task_out)

    return out


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    repo_id: uuid.UUID,
    data: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)

    task = Task(repository_id=repo_id, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return TaskOut.model_validate(task)


@router.post("/bulk", response_model=List[TaskOut], status_code=status.HTTP_201_CREATED)
async def bulk_create_tasks(
    repo_id: uuid.UUID,
    data: TaskBulkCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Bulk create tasks. Used both for manual bulk-add and to persist AI-extracted
    draft tasks once a human has reviewed them (see specs.py — spec upload only
    returns drafts, it never saves tasks directly)."""
    repo = await _assert_repo_owner(repo_id, user_id, db)

    spec: Optional[ProjectSpecification] = None
    if data.spec_id:
        spec_result = await db.execute(
            select(ProjectSpecification).where(
                ProjectSpecification.id == data.spec_id, ProjectSpecification.repository_id == repo_id
            )
        )
        spec = spec_result.scalar_one_or_none()
        if not spec:
            raise HTTPException(status_code=404, detail="Specification not found")

    tasks = []
    for i, td in enumerate(data.tasks):
        t = Task(repository_id=repo_id, spec_id=data.spec_id, order_index=i, **td.model_dump())
        db.add(t)
        tasks.append(t)

    if spec:
        spec.task_count = (spec.task_count or 0) + len(tasks)

    # Log activity
    log = ActivityLog(
        user_id=user_id,
        repository_id=repo_id,
        event_type=ActivityType.TASKS_GENERATED,
        title=f"Saved {len(tasks)} reviewed task(s) for {repo.name}"
        if spec
        else f"Generated {len(tasks)} tasks for {repo.name}",
        description=f"From specification: {spec.filename}" if spec else None,
    )
    db.add(log)

    await db.commit()
    for t in tasks:
        await db.refresh(t)

    return [TaskOut.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    repo_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.repository_id == repo_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut.model_validate(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    repo_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.repository_id == repo_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    # Log status changes
    if data.status:
        log = ActivityLog(
            user_id=user_id,
            repository_id=repo_id,
            event_type=ActivityType.TASK_UPDATED,
            title=f"Task '{task.title[:50]}' updated to {data.status.value}",
        )
        db.add(log)

    await db.commit()
    await db.refresh(task)
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    repo_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.repository_id == repo_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
