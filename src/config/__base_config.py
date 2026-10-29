import os
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_resource_path(relative_path):
    """Detecta si estamos en el EXE o en modo normal"""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


# --------------------------------------------------
def resolve_env_path() -> str:
    """Resuelve la ruta del archivo ``.env``.

    En el EXE compilado usa ``sys._MEIPASS`` vía ``get_resource_path``;
    en desarrollo se resuelve relativamente a este módulo
    (``src/.env``), sin depender del directorio de trabajo (CWD) desde
    el que se invoque la aplicación o una migración.

    Returns:
        Ruta absoluta al archivo ``.env``.
    """
    if getattr(sys, "_MEIPASS", None):
        return get_resource_path(os.path.join("src", ".env"))
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )


# -------------------------------------------------
class BaseAppSettings(BaseSettings):
    # _env_path = Path(__file__).resolve().parent.parent / ".env"
    _env_path = resolve_env_path()
    model_config = SettingsConfigDict(
        env_file=_env_path,
        env_file_encoding="utf-8",
        extra="allow",  # Permitir claves adicionales
    )
    APP_ENV: str = "dev"
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None
    SIIF_USERNAME: str | None = None
    SIIF_PASSWORD: str | None = None
    SSCC_USERNAME: str | None = None
    SSCC_PASSWORD: str | None = None
    SGF_USERNAME: str | None = None
    SGF_PASSWORD: str | None = None
    SGV_USERNAME: str | None = None
    SGV_PASSWORD: str | None = None
    BASE_URL: str = (
        "https://fixed-marita-invico-d13e43fa.koyeb.app"  # fallback si falta en .env
    )
    GOOGLE_CREDENTIALS: str | None = None  # JSON credentials for Google Sheets
    JWT_SECRET: str = "super_secret_key"
    DEFAULT_TIMEOUT: float = 90.0
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
