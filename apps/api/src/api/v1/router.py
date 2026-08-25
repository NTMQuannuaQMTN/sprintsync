"""Central API v1 router — mounts all sub-routers."""
from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.repositories import router as repos_router
from src.api.v1.tasks import router as tasks_router
from src.api.v1.specs import router as specs_router
from src.api.v1.suggestions import router as suggestions_router
from src.api.v1.webhook import router as webhook_router
from src.api.v1.dashboard import router as dashboard_router
from src.api.v1.activity import router as activity_router
from src.api.v1.commits import router as commits_router
from src.api.v1.intelligence import router as intelligence_router
from src.api.v1.pull_requests import router as pull_requests_router
from src.api.v1.summary import router as summary_router
from src.api.v1.integrations import router as integrations_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(repos_router)
api_router.include_router(tasks_router)
api_router.include_router(specs_router)
api_router.include_router(suggestions_router)
api_router.include_router(webhook_router)
api_router.include_router(activity_router)
api_router.include_router(commits_router)
api_router.include_router(intelligence_router)
api_router.include_router(pull_requests_router)
api_router.include_router(summary_router)
api_router.include_router(integrations_router)
