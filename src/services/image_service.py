from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.core.config import Settings, get_settings
from src.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.models.image import (
    CreateImageRequest,
    CreateImageResponse,
    DownloadUrlResponse,
    ImageMetadata,
    ListImagesQuery,
    ListImagesResponse,
    UploadStatus,
    Visibility,
    utcnow_iso,
    validate_image_id,
)
from src.repositories.image_repository import ImageRepository, map_item_to_metadata
from src.services.storage_service import StorageService


class ImageService:
    def __init__(
        self,
        repository: ImageRepository | None = None,
        storage_service: StorageService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or ImageRepository(self.settings)
        self.storage = storage_service or StorageService(self.settings)

    def create_image(self, owner_user_id: str, payload: CreateImageRequest) -> CreateImageResponse:
        if payload.content_type not in self.settings.allowed_content_types_set:
            raise BadRequestError("Unsupported content_type")
        if payload.size_bytes > self.settings.max_image_size_bytes:
            raise BadRequestError("Image size exceeds max_image_size_bytes")
        if len(payload.tags) > self.settings.max_tags:
            raise BadRequestError("Too many tags")
        if payload.caption and len(payload.caption) > self.settings.max_caption_length:
            raise BadRequestError("Caption too long")

        image_id = str(uuid4())
        created_at_str = utcnow_iso()
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).astimezone(UTC)
        s3_key = self.storage.build_s3_key(owner_user_id, image_id, payload.file_extension)

        metadata = ImageMetadata(
            image_id=image_id,
            owner_user_id=owner_user_id,
            visibility=payload.visibility,
            caption=payload.caption,
            tags=payload.tags,
            s3_key=s3_key,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            upload_status=UploadStatus.PENDING_UPLOAD,
            created_at=created_at,
            updated_at=created_at,
        )
        self.repository.create_image(metadata)
        upload_url, headers = self.storage.create_upload_url(s3_key=s3_key, content_type=payload.content_type)
        return CreateImageResponse(
            image_id=image_id,
            upload_url=upload_url,
            upload_headers=headers,
            metadata=metadata,
        )

    def list_images(self, caller_user_id: str, query: ListImagesQuery) -> ListImagesResponse:
        result = self.repository.list_images(user_id=caller_user_id, query=query)
        items = [map_item_to_metadata(item) for item in result.items]
        return ListImagesResponse(
            items=items,
            next_token=ListImagesQuery.encode_next_token(result.last_evaluated_key),
        )

    def get_image(self, caller_user_id: str, image_id: str) -> ImageMetadata:
        validate_image_id(image_id)
        item = self.repository.get_image_by_id(image_id)
        if item is None:
            raise NotFoundError("Image not found")
        self._assert_can_read(caller_user_id, item)
        return map_item_to_metadata(item)

    def get_download_url(self, caller_user_id: str, image_id: str) -> DownloadUrlResponse:
        image = self.get_image(caller_user_id=caller_user_id, image_id=image_id)
        url = self.storage.create_download_url(image.s3_key)
        return DownloadUrlResponse(
            image_id=image_id,
            download_url=url,
            expires_in=self.settings.presigned_url_expiry_seconds,
        )

    def delete_image(self, caller_user_id: str, image_id: str) -> None:
        validate_image_id(image_id)
        item = self.repository.get_image_by_id(image_id)
        if item is None:
            raise NotFoundError("Image not found")
        self._assert_owner(caller_user_id, item)
        self.repository.delete_image(item)
        self.storage.delete_object(item["s3Key"])

    @staticmethod
    def _assert_owner(caller_user_id: str, image_item: dict) -> None:
        if image_item["ownerUserId"] != caller_user_id:
            raise ForbiddenError("Only the owner can perform this action")

    def _assert_can_read(self, caller_user_id: str, image_item: dict) -> None:
        if image_item["ownerUserId"] == caller_user_id:
            return
        if image_item["visibility"] == Visibility.PUBLIC.value:
            return
        raise ForbiddenError("This image is private")
