from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BUSINESS_TZ = ZoneInfo("Europe/Moscow")

DEFAULT_ALLOWED_LINK_DOMAINS: frozenset[str] = frozenset(
    {
        "docs.google.com",
        "drive.google.com",
        "t.me",
        "telegram.me",
        "telegram.dog",
        "vk.com",
        "m.vk.com",
        "youtu.be",
        "youtube.com",
        "disk.yandex.ru",
        "disk.yandex.com",
        "yadi.sk",
        "github.com",
        "github.io",
        "notion.so",
        "notion.site",
        "dropbox.com",
        "innopolis.university",
        "www.innopolis.university",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Club League API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    database_url: str = Field(
        default="postgresql+asyncpg://club_league:club_league@127.0.0.1:5432/club_league",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")

    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    sso_authorize_url: str = Field(default="", alias="SSO_AUTHORIZE_URL")
    sso_token_url: str = Field(default="", alias="SSO_TOKEN_URL")
    sso_userinfo_url: str = Field(default="", alias="SSO_USERINFO_URL")
    sso_client_id: str = Field(default="", alias="SSO_CLIENT_ID")
    sso_client_secret: str = Field(default="", alias="SSO_CLIENT_SECRET")
    sso_redirect_uri: str = Field(
        default="http://localhost:5173/auth/callback",
        alias="SSO_REDIRECT_URI",
    )
    # Comma-separated browser origins allowed to call the API.
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:9001,http://127.0.0.1:9001",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:9001",
                "http://127.0.0.1:9001",
            ]
        return [part.strip() for part in raw.split(",") if part.strip()]

    deadline_soft_warning_days: int = Field(default=7, alias="DEADLINE_SOFT_WARNING_DAYS")
    # Comma-separated domains; use allowed_domains property for the parsed set.
    allowed_link_domains: str = Field(default="", alias="ALLOWED_LINK_DOMAINS")

    @property
    def allowed_domains(self) -> frozenset[str]:
        raw = self.allowed_link_domains.strip()
        if not raw:
            return DEFAULT_ALLOWED_LINK_DOMAINS
        return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
