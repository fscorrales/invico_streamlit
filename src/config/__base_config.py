from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# -------------------------------------------------
class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",  # Permitir claves adicionales
    )
    APP_ENV: str = "dev"
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    BASE_URL: str | None = None
    GOOGLE_CREDENTIALS: str | None = None  # JSON credentials for Google Sheets
    JWT_SECRET: str = "super_secret_key"
    # Otros valores opcionales...
    # HOST_URL: str = "localhost"
    # HOST_PORT: int = 8000
    # FRONTEND_HOST: str = "localhost"

    # -------------------------------------------------
    @property
    def debug(self) -> bool:
        return self.APP_ENV == "dev"


# class DevSettings(BaseAppSettings):
#     debug: bool = True


# class ProdSettings(BaseAppSettings):
#     debug: bool = False


# if APP_ENV == "prod":
#     settings = ProdSettings()
# else:
#     settings = DevSettings()

settings = BaseAppSettings()
