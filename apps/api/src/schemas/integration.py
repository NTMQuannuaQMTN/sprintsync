"""Integration Pydantic schemas. access_token/refresh_token are write-only
(accepted on connect) and never appear in any response — same treatment
as GitHub tokens elsewhere in this codebase."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.models.integration import IntegrationType


class NotionConnectRequest(BaseModel):
    access_token: str
    database_id: str
    title_property: str = "Name"
    status_property: str = "Status"
    workspace_name: Optional[str] = None


class IntegrationOut(BaseModel):
    id: uuid.UUID
    integration_type: IntegrationType
    workspace_name: Optional[str] = None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
