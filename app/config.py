"""
Centralized application settings, loaded from environment variables (.env).
Keeping all config in one place makes it obvious what needs to be set
before deploying, and avoids scattering os.getenv() calls everywhere.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Defaults to a local SQLite file so the project runs out-of-the-box
    # without requiring a Postgres install. Override with a real Postgres
    # URL in .env for anything beyond local development.
    database_url: str = "sqlite:///./workout_tracker.db"

    secret_key: str = "dev-secret-key-do-not-use-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
