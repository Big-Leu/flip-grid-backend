"""
For all modules, add the routers in this file.

"""

from fastapi.routing import APIRouter  # type: ignore

from backend.api.modules import (
    health,
    monitoring,
    swagger,
    test,
    users,
    form,
)

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(users.oauth_router)
api_router.include_router(users.views_router)
api_router.include_router(swagger.router)
api_router.include_router(health.router)
api_router.include_router(test.router)
api_router.include_router(
    form.router,
    prefix="/form",
    tags=["form"],
)
