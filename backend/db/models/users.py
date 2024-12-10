# type: ignore
import uuid
from typing import Any, List

from fastapi import Depends, Response, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.authentication.strategy import Strategy
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)
from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)
from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyAccessTokenDatabase,
    SQLAlchemyBaseAccessTokenTableUUID,
)
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.dependencies import get_db_session
from backend.settings import settings

# Add all custom columns/fields to the User model in the following models


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"
    userName: Mapped[str] = mapped_column(String, nullable=True)
    mobileNumber: Mapped[str] = mapped_column(String, nullable=True)
    userAadhar: Mapped[str] = mapped_column(String, nullable=True)
    userDrivingLicense: Mapped[str] = mapped_column(String, nullable=True)
    userProfile: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )  # Add this column to store user profile information # noqa: E501

    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(
        "OAuthAccount",
        lazy="joined",
    )


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    pass


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Represents a read command for a user."""


class UserCreate(schemas.BaseUserCreate):
    """Represents a create command for a user."""


class UserUpdate(schemas.BaseUserUpdate):
    """Represents an update command for a user."""


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Manages a user session and its tokens."""

    reset_password_token_secret = settings.users_secret
    verification_token_secret = settings.users_secret


# End of model schemas


async def get_access_token_db(
    session: AsyncSession = Depends(get_db_session),
):
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)


async def get_user_db(  # It returns a DB instance for the user database
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyUserDatabase:
    """
    Yield a SQLAlchemyUserDatabase instance.

    :param session: asynchronous SQLAlchemy session.
    :yields: instance of SQLAlchemyUserDatabase.
    """
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> UserManager:
    """
    Yield a UserManager instance.

    :param user_db: SQLAlchemy user db instance
    :yields: an instance of UserManager.
    """
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    # It returns a JWTStrategy instance, it can be
    # used to create jwt tokens for authentication
    """
    Return a JWTStrategy in order to instantiate it dynamically.

    :returns: instance of JWTStrategy with provided settings.
    """
    return JWTStrategy(secret=settings.users_secret, lifetime_seconds=172800)


def get_database_strategy(
    access_token_db: AccessTokenDatabase[AccessToken] = Depends(get_access_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=172800)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
auth_jwt = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

cookie_transport = CookieTransport(cookie_max_age=172800)

auth_cookie = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_database_strategy,
)


class AutoRedirectCookieBackend(AuthenticationBackend):
    async def login(self, strategy: Strategy, user: Any) -> Response:
        response = await super().login(strategy, user)
        response.status_code = status.HTTP_302_FOUND
        response.headers["Location"] = settings.REDIRECT_LOGIN_URL
        return response


auth_sso_cookie = AutoRedirectCookieBackend(
    name="sso_cookie",
    transport=cookie_transport,
    get_strategy=get_database_strategy,
)

backends = [
    auth_cookie,
    auth_jwt,
    auth_sso_cookie,
]


async def logout_current_user(user: User) -> None:
    """
    Logout the current user.

    :param user: user to logout.
    """
    auth_cookie.logout(get_jwt_strategy, user)


api_users = FastAPIUsers[User, uuid.UUID](get_user_manager, backends)

current_active_user = api_users.current_user(active=True)
google_oauth_client = GoogleOAuth2(
    settings.CLIENT_ID,
    settings.CLIENT_SECRET,
)
