"""Project Specification upload and processing endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.models.project_spec import ProjectSpecification, SpecStatus
from src.models.task import Task
from src.models.activity_log import ActivityLog, ActivityType
from src.schemas.project_spec import SpecOut
from src.schemas.task import TaskOut
from src.services.document_parser import extract_text
from src.services.ai import ai_service

router = APIRouter(prefix="/repositories/{repo_id}/specs", tags=["specs"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=List[SpecOut])
async def list_specs(
    repo_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(ProjectSpecification)
        .where(ProjectSpecification.repository_id == repo_id)
        .order_by(ProjectSpecification.created_at.desc())
    )
    return [SpecOut.model_validate(s) for s in result.scalars().all()]


@router.post("", response_model=SpecOut, status_code=status.HTTP_201_CREATED)
async def upload_spec(
    repo_id: uuid.UUID,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a project specification document (PDF or DOCX)."""
    repo = await _assert_repo_owner(repo_id, user_id, db)

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES and not (
        (file.filename or "").lower().endswith((".pdf", ".docx", ".doc"))
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported",
        )

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB.")

    # Create spec record
    storage_path = f"{repo_id}/{uuid.uuid4()}/{file.filename}"
    spec = ProjectSpecification(
        repository_id=repo_id,
        filename=file.filename or "document",
        file_size=len(file_bytes),
        mime_type=content_type or "application/octet-stream",
        storage_path=storage_path,
        status=SpecStatus.PROCESSING,
    )
    db.add(spec)
    await db.commit()
    await db.refresh(spec)

    # Try Supabase upload (non-blocking if not configured)
    from src.core.config import settings
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client  # type: ignore
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            supabase.storage.from_(settings.SUPABASE_BUCKET).upload(storage_path, file_bytes)
            signed = supabase.storage.from_(settings.SUPABASE_BUCKET).create_signed_url(storage_path, 86400)
            spec.storage_url = signed.get("signedURL")
        except Exception:
            pass  # storage is optional for MVP

    # Extract text
    extracted_text, error = await extract_text(file_bytes, content_type, file.filename or "")
    if error:
        spec.status = SpecStatus.ERROR
        spec.error_message = error
        await db.commit()
        return SpecOut.model_validate(spec)

    spec.extracted_text = extracted_text

    # AI task extraction — these are DRAFTS ONLY. Nothing is written to the
    # tasks table here; the human must review and confirm via
    # POST /repositories/{repo_id}/tasks/bulk (with spec_id set) before any
    # Task row is created. task_count stays 0 until that confirmation happens.
    draft_tasks = await ai_service.extract_tasks_from_text(extracted_text, repo.name)

    spec.status = SpecStatus.DONE
    spec.task_count = 0
    spec.ai_summary = (
        f"AI extracted {len(draft_tasks)} draft task(s) from {file.filename}. "
        f"Review and save the ones you want to keep."
    )

    # Activity log
    log = ActivityLog(
        user_id=user_id,
        repository_id=repo_id,
        event_type=ActivityType.SPEC_UPLOADED,
        title=f"Uploaded specification: {file.filename}",
        description=f"AI drafted {len(draft_tasks)} tasks pending review",
    )
    db.add(log)

    await db.commit()
    await db.refresh(spec)

    out = SpecOut.model_validate(spec)
    out.draft_tasks = draft_tasks
    return out


@router.get("/{spec_id}/tasks", response_model=List[TaskOut])
async def get_spec_tasks(
    repo_id: uuid.UUID,
    spec_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all tasks generated from a specific spec."""
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Task)
        .where(Task.spec_id == spec_id, Task.repository_id == repo_id)
        .order_by(Task.order_index)
    )
    return [TaskOut.model_validate(t) for t in result.scalars().all()]
