"""Integration connect/list/disconnect endpoints (V2 Phase 7 wiring).

Closes the gap between "NotionBoardProvider exists and is unit-tested"
and "a real user can actually connect a Notion workspace" — connecting
performs a real, live verification call against Notion before persisting
anything, so a wrong token/database_id is rejected immediately rather than
silently stored.
"""
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.integration import Integration, IntegrationType
from src.schemas.integration import IntegrationOut, NotionConnectRequest
from src.services.taskboard.notion import NotionBoardProvider

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationOut])
async def list_integrations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Integration).where(Integration.user_id == user_id))
    return [IntegrationOut.model_validate(i) for i in result.scalars().all()]


@router.post("/notion/connect", response_model=IntegrationOut)
async def connect_notion(
    body: NotionConnectRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Verifies the token can actually resolve the given Notion database
    before saving anything (a real network call, not a format check) —
    this is the same request NotionBoardProvider makes at first use, just
    performed eagerly so a bad credential fails loudly at connect time
    instead of silently at the next suggestion approval."""
    provider = NotionBoardProvider(token=body.access_token, database_id=body.database_id)
    try:
        await provider.verify_connection()
    except Exception as e:
        logger.warning("integrations.notion_verification_failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Could not verify this Notion token/database — {e}",
        )
    finally:
        await provider.close()

    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user_id, Integration.integration_type == IntegrationType.NOTION
        )
    )
    integration = result.scalar_one_or_none()
    if integration is None:
        integration = Integration(user_id=user_id, integration_type=IntegrationType.NOTION)
        db.add(integration)

    integration.access_token = body.access_token
    integration.workspace_name = body.workspace_name
    integration.active = True
    integration.config = {
        "database_id": body.database_id,
        "title_property": body.title_property,
        "status_property": body.status_property,
    }

    await db.commit()
    await db.refresh(integration)
    return IntegrationOut.model_validate(integration)


@router.delete("/notion", status_code=204)
async def disconnect_notion(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user_id, Integration.integration_type == IntegrationType.NOTION
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="No Notion integration connected")
    integration.active = False
    integration.access_token = None
    await db.commit()
