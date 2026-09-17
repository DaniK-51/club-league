from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    client_id: str = "club-league-dev"
    client_secret: str = "club-league-dev-secret"
    code_ttl_seconds: int = 300
    token_ttl_seconds: int = 600

    # Browser-facing URLs for the built-in SSO demo pages.
    self_base_url: str = "http://127.0.0.1:9001"
    api_base_url: str = "http://127.0.0.1:8000"
    demo_redirect_uri: str = ""  # default: {self_base_url}/callback


settings = Settings()


def demo_redirect() -> str:
    return settings.demo_redirect_uri or f"{settings.self_base_url.rstrip('/')}/callback"
