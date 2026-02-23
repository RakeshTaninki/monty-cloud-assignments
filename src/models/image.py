import base64
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Visibility(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class CreateImageRequest(BaseModel):
    caption: str | None = Field(default=None, max_length=2200)
    tags: list[str] = Field(default_factory=list, max_length=10)
    visibility: Visibility = Visibility.PRIVATE
    content_type: str = Field(..., pattern=r"^image\/[a-zA-Z0-9.+-]+$")
    size_bytes: int = Field(..., gt=0, le=10_485_760)
    file_extension: str = Field(..., pattern=r"^[a-zA-Z0-9]+$")

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in value:
            clean = tag.strip().lower()
            if not clean:
                continue
            if len(clean) > 64:
                raise ValueError("Each tag must be at most 64 chars")
            if clean in seen:
                continue
            seen.add(clean)
            normalized.append(clean)
        return normalized


class CreateImageResponse(BaseModel):
    image_id: str
    upload_url: str
    upload_headers: dict[str, str]
    metadata: "ImageMetadata"


class ListImagesQuery(BaseModel):
    visibility: Visibility | None = None
    tag: str | None = None
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)
    next_token: str | None = None

    @field_validator("tag")
    @classmethod
    def normalize_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip().lower()
        if not clean:
            return None
        if len(clean) > 64:
            raise ValueError("Tag must be at most 64 chars")
        return clean

    @model_validator(mode="after")
    def validate_range(self) -> "ListImagesQuery":
        if self.from_ts and self.to_ts and self.from_ts > self.to_ts:
            raise ValueError("'from' must be before or equal to 'to'")
        return self

    def decode_next_token(self) -> dict[str, Any] | None:
        if not self.next_token:
            return None
        raw = base64.urlsafe_b64decode(self.next_token.encode("utf-8")).decode("utf-8")
        return json.loads(raw)

    @staticmethod
    def encode_next_token(last_key: dict[str, Any] | None) -> str | None:
        if not last_key:
            return None
        raw = json.dumps(last_key, separators=(",", ":"), default=str)
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


class ImageMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_id: str
    owner_user_id: str
    visibility: Visibility
    caption: str | None
    tags: list[str]
    s3_key: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class ListImagesResponse(BaseModel):
    items: list[ImageMetadata]
    next_token: str | None = None


class DownloadUrlResponse(BaseModel):
    image_id: str
    download_url: str
    expires_in: int


def utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_image_id(image_id: str) -> str:
    UUID(image_id)
    return image_id
