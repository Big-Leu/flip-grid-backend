import enum
import logging
import os
from datetime import timedelta
from pathlib import Path
from tempfile import gettempdir
from typing import ClassVar

from cachetools import TTLCache
from catilo import catilo  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
from yarl import URL  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_DIR = Path(gettempdir())


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cfg = catilo.VariableDirectory()

cfg.add_file_source("DefaultConfig", 10, "default.yml")

try:
    cfg.add_file_source("MainConfig", 5, "config.yml")
except Exception:
    logger.warning("No config file found, using default")

cfg.enable_environment_vars("AUDITROL_", strip=True)

logger.info(cfg.variables)


class LogLevel(str, enum.Enum):  # noqa: WPS600
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    JWT_SECRET: str = cfg.get("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_TOKEN_EXPIRE_MINUTES", 60))
    REDIRECT_LOGIN_URL: str = cfg.get("REDIRECT_LOGIN_URL")
    REDIRECT_CALLBACK_URL: str = cfg.get("REDIRECT_CALLBACK_URL")
    FAILED_LOGIN_ROUTE: str = cfg.get("FAILED_LOGIN_ROUTE")
    cookie_domain: str = cfg.get("cookie_domain")
    ACCESS_KEY: str = cfg.get("ACCESS_KEY")
    SECRET_KEY: str = cfg.get("SECRET_KEY")
    REGION: str = cfg.get("REGION")
    host: str = cfg.get("host")
    port: int = cfg.get("port")
    # quantity of workers for uvicorn
    workers_count: int = 1
    # Enable uvicorn reloading
    reload: bool = True

    # Current environment
    environment: str = "dev"

    log_level: LogLevel = LogLevel.INFO
    users_secret: str = os.getenv("USERS_SECRET", "")
    # Variables for the database
    db_host: str = cfg.get("db_host")
    db_port: int = cfg.get("db_port")
    db_user: str = cfg.get("db_user")
    db_pass: str = cfg.get("db_pass")
    db_base: str = cfg.get("db_base")
    db_echo: bool = False
    cache: ClassVar[TTLCache] = TTLCache(
        cfg.get("CACHE_MAXSIZE"), ttl=timedelta(hours=cfg.get("CACHE_TIMEOUT_HOUR"))
    )
    TF_ENABLE_ONEDNN_OPTS: int = cfg.get("TF_ENABLE_ONEDNN_OPTS")
    CLIENT_ID: str = cfg.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET: str = cfg.get("GOOGLE_CLIENT_SECRET")
    # This variable is used to define
    # multiproc_dir. It's required for [uvi|guni]corn projects.
    prometheus_dir: Path = TEMP_DIR / "prom"
    CORS_ORGIN: list[str] = cfg.get("CORS_ORGIN")

    @property
    def db_url(self) -> URL:
        """
        Assemble database URL from settings.

        :return: database URL.
        """
        dburl = URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}",
        )
        print(str(dburl))
        return dburl

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BACKEND_",
        env_file_encoding="utf-8",
    )


settings = Settings()
