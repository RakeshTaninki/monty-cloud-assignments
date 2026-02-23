from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "secure-image-service"
    app_env: Literal["local", "dev", "prod"] = "local"
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None
    s3_addressing_style: Literal["auto", "path", "virtual"] = "auto"
    images_table_name: str = "Images"
    images_bucket_name: str = "images-bucket"
    gsi1_name: str = "GSI1ImageLookup"
    gsi2_name: str = "GSI2UserVisibility"
    presigned_url_expiry_seconds: int = Field(default=900, ge=60, le=3600)
    pending_upload_ttl_extra_seconds: int = Field(default=900, ge=0, le=86_400)
    max_tags: int = Field(default=10, ge=1, le=20)
    max_caption_length: int = Field(default=2200, ge=1, le=5000)
    max_page_size: int = Field(default=50, ge=1, le=100)
    max_image_size_bytes: int = Field(default=10_485_760, ge=1024)
    allow_insecure_test_auth: bool = False
    allowed_content_types: str = "image/jpeg,image/png,image/webp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_content_types_set(self) -> set[str]:
        return {item.strip() for item in self.allowed_content_types.split(",") if item.strip()}

    @property
    def aws_endpoint_url_or_none(self) -> str | None:
        if not self.aws_endpoint_url:
            return None
        return self.aws_endpoint_url.strip() or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
