from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ALI Simulations"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://ali:ali@localhost:5432/ali_simulations"
    secret_key: str = "change-me-in-production"
    access_token_minutes: int = 60
    frontend_url: str = "http://localhost:5173"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_first_name: str = "Platform"
    bootstrap_admin_last_name: str = "Administrator"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        # Render supplies postgresql://; psycopg3/SQLAlchemy prefers postgresql+psycopg://
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

settings = Settings()
