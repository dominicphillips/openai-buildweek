from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and an optional local .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    chatkit_domain_key: str | None = Field(
        default=None,
        alias="SOMETHINGS_ON_CHATKIT_DOMAIN_KEY",
    )
    agent_model: str = Field(default="gpt-5.6", alias="SOMETHINGS_ON_AGENT_MODEL")
    image_model: str = Field(default="gpt-image-2", alias="SOMETHINGS_ON_IMAGE_MODEL")
    database_path: Path = Field(
        default=Path("data/somethings-on.sqlite3"),
        alias="SOMETHINGS_ON_DATABASE_PATH",
    )
    asset_path: Path = Field(
        default=Path("data/assets"),
        alias="SOMETHINGS_ON_ASSET_PATH",
    )
    reference_catalog_manifest_path: Path = Field(
        default=BACKEND_ROOT / "seeds" / "reference_catalog.json",
        alias="SOMETHINGS_ON_REFERENCE_CATALOG_MANIFEST_PATH",
    )
    reference_catalog_database_path: Path = Field(
        default=BACKEND_ROOT / "data" / "reference-catalog.lancedb",
        alias="SOMETHINGS_ON_REFERENCE_CATALOG_DATABASE_PATH",
    )
    casting_presets_path: Path = Field(
        default_factory=lambda: (
            Path(__file__).resolve().parents[2] / "seeds" / "casting_presets.json"
        ),
        alias="SOMETHINGS_ON_CASTING_PRESETS_PATH",
    )
    allowed_origin: str = Field(
        default="http://127.0.0.1:43173",
        alias="SOMETHINGS_ON_ALLOWED_ORIGIN",
    )
    max_upload_bytes: int = Field(
        default=12 * 1024 * 1024,
        alias="SOMETHINGS_ON_MAX_UPLOAD_BYTES",
        ge=1,
    )

    @property
    def api_key_value(self) -> str | None:
        if self.openai_api_key is None:
            return None
        value = self.openai_api_key.get_secret_value().strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
