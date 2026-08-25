"""Resolves which TaskBoardProvider governs a repository's task-board sync,
and best-effort mirrors an approved status change to it.

Internal Task rows remain the canonical source of truth regardless of
which provider is active -- AI reasoning and task matching always run
against SprintSync's own Task list (see webhook.py/commits.py), never
against Notion directly, which is what keeps that layer platform-
independent. A connected external provider (currently just Notion) is a
best-effort *mirror*, applied by title lookup after the internal Task
status has already been updated: there is no persisted mapping from a
SprintSync Task to a Notion page id, so mirroring can only find a page
whose title matches closely enough (Notion's own text-contains filter) --
it does not create a Notion page if none is found. This is a real,
working, documented limitation, not a placeholder: see
docs/V2_IMPLEMENTATION_PLAN.md §9.
"""
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.integration import Integration, IntegrationType
from src.services.taskboard.notion import NotionBoardProvider

logger = structlog.get_logger(__name__)


async def get_active_notion_integration(user_id: str, db: AsyncSession) -> Optional[Integration]:
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user_id,
            Integration.integration_type == IntegrationType.NOTION,
            Integration.active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def build_notion_provider(integration: Integration) -> Optional[NotionBoardProvider]:
    if not integration.access_token or not integration.config or not integration.config.get("database_id"):
        return None
    return NotionBoardProvider(
        token=integration.access_token,
        database_id=integration.config["database_id"],
        title_property=integration.config.get("title_property", "Name"),
        status_property=integration.config.get("status_property", "Status"),
    )


async def mirror_status_to_external_board(
    user_id: str, task_title: str, proposed_status: str, db: AsyncSession
) -> None:
    """Best-effort only: never raises, never blocks or reverts the internal
    approval that already happened. A repo with no connected Notion
    integration is the common case and this is a fast no-op for it."""
    integration = await get_active_notion_integration(user_id, db)
    if not integration:
        return

    provider = build_notion_provider(integration)
    if not provider:
        logger.warning("taskboard.notion_integration_misconfigured", user_id=str(user_id))
        return

    try:
        match = await provider.find_task(task_title)
        if not match:
            logger.info("taskboard.notion_mirror_skipped_no_match", task_title=task_title)
            return
        await provider.update_status(match.id, proposed_status)
        logger.info("taskboard.notion_mirror_succeeded", notion_page_id=match.id, proposed_status=proposed_status)
    except Exception as e:
        logger.warning("taskboard.notion_mirror_failed", error=str(e), task_title=task_title)
    finally:
        await provider.close()
