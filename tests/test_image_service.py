from datetime import UTC, datetime

import pytest

from src.core.exceptions import ForbiddenError
from src.models.image import CreateImageRequest, Visibility
from src.services.image_service import ImageService


class FakeRepo:
    def __init__(self) -> None:
        self.created = None
        self.item = None
        self.deleted = None

    def create_image(self, image):
        self.created = image

    def get_image_by_id(self, image_id: str):
        return self.item

    def list_images(self, user_id: str, query):
        return type("ListResult", (), {"items": [], "last_evaluated_key": None})()

    def delete_image(self, image):
        self.deleted = image


class FakeStorage:
    def build_s3_key(self, owner_user_id: str, image_id: str, file_extension: str) -> str:
        return f"images/{owner_user_id}/{image_id}.{file_extension}"

    def create_upload_url(self, s3_key: str, content_type: str):
        return "https://upload.example", {"Content-Type": content_type, "key": s3_key}

    def create_download_url(self, s3_key: str):
        return "https://download.example"

    def delete_object(self, s3_key: str):
        return None


def test_create_image_success():
    repo = FakeRepo()
    service = ImageService(repository=repo, storage_service=FakeStorage())
    payload = CreateImageRequest(
        caption="test",
        tags=["TagOne", "tagone", "tagtwo"],
        visibility=Visibility.PRIVATE,
        content_type="image/jpeg",
        size_bytes=1024,
        file_extension="jpg",
    )

    response = service.create_image("user-1", payload)

    assert response.image_id
    assert response.upload_url.startswith("https://upload.example")
    assert repo.created.tags == ["tagone", "tagtwo"]
    assert repo.created.owner_user_id == "user-1"
    assert response.metadata.upload_status.value == "PENDING_UPLOAD"


def test_non_owner_cannot_read_private():
    repo = FakeRepo()
    repo.item = {
        "PK": "USER#owner-1",
        "SK": "IMAGE#2026-02-22T10:10:10Z#img",
        "imageId": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
        "ownerUserId": "owner-1",
        "visibility": "PRIVATE",
        "caption": "",
        "tags": ["_none"],
        "s3Key": "images/owner-1/id.jpg",
        "contentType": "image/jpeg",
        "sizeBytes": 10,
        "createdAt": "2026-02-22T10:10:10Z",
        "updatedAt": "2026-02-22T10:10:10Z",
    }
    service = ImageService(repository=repo, storage_service=FakeStorage())

    with pytest.raises(ForbiddenError):
        service.get_image("other-user", "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")


def test_non_owner_can_read_public():
    repo = FakeRepo()
    repo.item = {
        "PK": "USER#owner-1",
        "SK": "IMAGE#2026-02-22T10:10:10Z#img",
        "imageId": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
        "ownerUserId": "owner-1",
        "visibility": "PUBLIC",
        "caption": "",
        "tags": ["_none"],
        "s3Key": "images/owner-1/id.jpg",
        "contentType": "image/jpeg",
        "sizeBytes": 10,
        "createdAt": "2026-02-22T10:10:10Z",
        "updatedAt": "2026-02-22T10:10:10Z",
    }
    service = ImageService(repository=repo, storage_service=FakeStorage())

    metadata = service.get_image("other-user", "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb")

    assert metadata.visibility.value == "PUBLIC"
    assert metadata.owner_user_id == "owner-1"


def test_delete_owner_only():
    repo = FakeRepo()
    repo.item = {
        "PK": "USER#owner-1",
        "SK": "IMAGE#2026-02-22T10:10:10Z#img",
        "imageId": "cccccccc-cccc-4ccc-cccc-cccccccccccc",
        "ownerUserId": "owner-1",
        "visibility": "PRIVATE",
        "caption": "",
        "tags": ["_none"],
        "s3Key": "images/owner-1/id.jpg",
        "contentType": "image/jpeg",
        "sizeBytes": 10,
        "createdAt": "2026-02-22T10:10:10Z",
        "updatedAt": "2026-02-22T10:10:10Z",
    }
    service = ImageService(repository=repo, storage_service=FakeStorage())

    with pytest.raises(ForbiddenError):
        service.delete_image("other-user", "cccccccc-cccc-4ccc-cccc-cccccccccccc")

    service.delete_image("owner-1", "cccccccc-cccc-4ccc-cccc-cccccccccccc")
    assert repo.deleted["ownerUserId"] == "owner-1"
