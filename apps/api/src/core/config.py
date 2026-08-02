"""Application configuration via environment variables."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    ENV: str = "development"
    APP_NAME: str = "SprintSync AI"

    # Database — points at the Supabase project's Postgres connection string
    # (Supabase dashboard: Settings > Database > Connection string), using
    # the service_role-equivalent DB user so our own queries bypass RLS
    # (RLS protects the direct PostgREST/supabase-js access path, not a
    # trusted backend — see the RLS policies in alembic/versions/001_*.py).
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sprintsync"

    # GitHub Webhook — still handled by this app directly (Supabase Auth only
    # owns the OAuth *login* flow, not GitHub webhook delivery).
    GITHUB_WEBHOOK_SECRET: str = ""

    # Supabase — GitHub OAuth itself is configured in the Supabase dashboard
    # (Authentication > Providers > GitHub), not here. This app only needs to
    # (a) verify the JWTs Supabase issues, and (b) optionally use the
    # service-role key for Supabase Storage (spec uploads).
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_BUCKET: str = "sprintsync-specs"

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        origins = [self.FRONTEND_URL]
        if self.ENV == "development":
            origins += ["http://localhost:3000", "http://127.0.0.1:3000"]
        return origins


settings = Settings()
