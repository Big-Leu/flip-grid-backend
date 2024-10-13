from typing import Tuple, Type

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_users import models
from fastapi_users.authentication import Strategy
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt
from fastapi_users.manager import BaseUserManager
from fastapi_users.router.common import ErrorCode
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallback
from httpx_oauth.oauth2 import OAuth2Token

from backend.commons.responses import JSONResponse
from backend.db.models.users import api_users, auth_sso_cookie, google_oauth_client
from backend.settings import settings

STATE_TOKEN_AUDIENCE = "fastapi-users:oauth-state"

try:
    from httpx_oauth.oauth2 import BaseOAuth2

except ModuleNotFoundError:  # pragma: no cover
    BaseOAuth2 = Type  # type: ignore


router = APIRouter()


@router.get("/auth/call", response_model=None)
async def callback(
    request: Request,
    user_manager: BaseUserManager[models.UP, models.ID] = Depends(
        api_users.get_user_manager
    ),
    strategy: Strategy[models.UP, models.ID] = Depends(auth_sso_cookie.get_strategy),
):
    is_access_denied = request.query_params.get("error", False)

    if is_access_denied:
        return JSONResponse(
            content={"message": "Login failed"},
            status_code=302,
            headers={"Location": settings.FAILED_LOGIN_ROUTE},
        )

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    oauth_callback_instance = OAuth2AuthorizeCallback(
        google_oauth_client,
        redirect_url=settings.REDIRECT_CALLBACK_URL,
    )

    access_token_state: Tuple[OAuth2Token, str] = await oauth_callback_instance(
        request=request, code=code, state=state
    )
    token, state = access_token_state
    account_id, account_email = await google_oauth_client.get_id_email(
        token["access_token"]
    )
    if account_email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.OAUTH_NOT_AVAILABLE_EMAIL,
            headers={"Location": ""},
        )

    try:
        decode_jwt(state, settings.JWT_SECRET, [STATE_TOKEN_AUDIENCE])
    except jwt.DecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        user = await user_manager.oauth_callback(
            google_oauth_client.name,
            token["access_token"],
            account_id,
            account_email,
            token.get("expires_at"),
            token.get("refresh_token"),
            request,
            associate_by_email=True,
            is_verified_by_default=True,
        )
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.OAUTH_USER_ALREADY_EXISTS,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            # headers={"Location": failed_login_route},
        )

    # Authenticate
    response = await auth_sso_cookie.login(strategy, user)
    await user_manager.on_after_login(user, request, response)
    return response
