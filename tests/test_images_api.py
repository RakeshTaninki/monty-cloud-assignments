from fastapi.testclient import TestClient

from src.api.images import get_image_service
from src.core.security import AuthContext, get_auth_context
from src.main import create_app
from src.models.image import Visibility


class FakeImageService:
    def __init__(self) -> None:
        self.deleted = False

    def create_image(self, owner_user_id, payload):
        return {
            "image_id": "11111111-1111-4111-8111-111111111111",
            "upload_url": "https://upload.example",
            "upload_headers": {"Content-Type": payload.content_type},
            "metadata": {
                "image_id": "11111111-1111-4111-8111-111111111111",
                "owner_user_id": owner_user_id,
                "visibility": payload.visibility.value,
                "caption": payload.caption,
                "tags": payload.tags,
                "s3_key": "images/user/1.jpg",
                "content_type": payload.content_type,
                "size_bytes": payload.size_bytes,
                "upload_status": "PENDING_UPLOAD",
                "uploaded_at": None,
                "created_at": "2026-02-22T10:10:10Z",
                "updated_at": "2026-02-22T10:10:10Z",
            },
        }

    def list_images(self, caller_user_id, query):
        return {"items": [], "next_token": None}

    def get_image(self, caller_user_id, image_id):
        return {
            "image_id": image_id,
            "owner_user_id": "owner-1",
            "visibility": Visibility.PUBLIC.value,
            "caption": None,
            "tags": [],
            "s3_key": "images/user/1.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 100,
            "upload_status": "UPLOADED",
            "uploaded_at": "2026-02-22T10:11:10Z",
            "created_at": "2026-02-22T10:10:10Z",
            "updated_at": "2026-02-22T10:10:10Z",
        }

    def get_download_url(self, caller_user_id, image_id):
        return {
            "image_id": image_id,
            "download_url": "https://download.example",
            "expires_in": 900,
        }

    def delete_image(self, caller_user_id, image_id):
        self.deleted = True


def _override_auth():
    return AuthContext(user_id="user-123")


def _create_client() -> TestClient:
    app = create_app()
    fake_service = FakeImageService()
    app.dependency_overrides[get_auth_context] = _override_auth
    app.dependency_overrides[get_image_service] = lambda: fake_service
    return TestClient(app)


def test_create_image_validation_error():
    client = _create_client()
    payload = {
        "caption": "demo",
        "tags": [],
        "visibility": "PRIVATE",
        "content_type": "application/pdf",
        "size_bytes": 100,
        "file_extension": "pdf",
    }

    response = client.post("/v1/images", json=payload)
    assert response.status_code == 422


def test_create_image_success():
    client = _create_client()
    payload = {
        "caption": "demo",
        "tags": ["sunset"],
        "visibility": "PRIVATE",
        "content_type": "image/jpeg",
        "size_bytes": 100,
        "file_extension": "jpg",
    }

    response = client.post("/v1/images", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["metadata"]["owner_user_id"] == "user-123"


def test_list_images():
    client = _create_client()
    response = client.get("/v1/images?limit=10")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_get_download_url():
    client = _create_client()
    image_id = "22222222-2222-4222-8222-222222222222"
    response = client.get(f"/v1/images/{image_id}/download-url")
    assert response.status_code == 200
    assert "download_url" in response.json()
