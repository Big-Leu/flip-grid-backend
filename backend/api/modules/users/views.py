from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.commons.responses import ServiceResponse
from backend.db.dependencies import get_db_session
from backend.db.models.users import UserCreate, UserRead, api_users  # type: ignore
from backend.db.models.users import auth_sso_cookie, auth_cookie  # type: ignore
from backend.db.models.users import google_oauth_client  # type: ignore
from backend.db.models.users import (  # type: ignore
    User,
    current_active_user,
)
from backend.services.commons.base import BaseService
from backend.services.google_oauth.crud import GoogleAPIService
from backend.settings import settings  # type: ignore

router = APIRouter()

router.include_router(
    api_users.get_auth_router(auth_cookie),
    prefix="/auth/jwt",
    tags=["auth"],
)

router.include_router(
    api_users.get_oauth_router(
        google_oauth_client,
        auth_sso_cookie,
        settings.JWT_SECRET,
        redirect_url=settings.REDIRECT_CALLBACK_URL,
        is_verified_by_default=True,
        associate_by_email=True,
    ),
    prefix="/auth/google",
    tags=["auth"],
)

router.include_router(
    api_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)


@router.get("/whoami", response_model=None)
async def user_data(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> ServiceResponse:
    bp_service = GoogleAPIService(db)
    return await bp_service.Read(user.email, user.id)


@router.get("/userdata", response_model=None)
async def user_data(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> ServiceResponse:
    bp_service = BaseService(db).get_user_details(user.id)
    return await bp_service
