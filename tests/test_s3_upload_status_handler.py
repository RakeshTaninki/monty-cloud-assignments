from src.handlers import s3_upload_status_handler as handler


def test_parse_s3_key_success():
    parsed = handler.parse_s3_key("images/user-1/123e4567-e89b-42d3-a456-426614174000.jpg")
    assert parsed == ("user-1", "123e4567-e89b-42d3-a456-426614174000")


def test_parse_s3_key_invalid():
    assert handler.parse_s3_key("invalid/key.jpg") is None
    assert handler.parse_s3_key("images/user-1/not-a-uuid.jpg") is None


def test_lambda_handler_marks_uploaded(monkeypatch):
    class FakeRepo:
        def __init__(self):
            self.calls = []

        def mark_uploaded(self, owner_user_id: str, image_id: str, uploaded_at: str) -> None:
            self.calls.append((owner_user_id, image_id, uploaded_at))

    fake_repo = FakeRepo()
    monkeypatch.setattr(handler, "ImageRepository", lambda: fake_repo)

    event = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {"object": {"key": "images/user-1/123e4567-e89b-42d3-a456-426614174000.jpg"}},
            },
            {
                "eventName": "ObjectRemoved:Delete",
                "s3": {"object": {"key": "images/user-1/123e4567-e89b-42d3-a456-426614174000.jpg"}},
            },
        ]
    }
    result = handler.lambda_handler(event, None)

    assert result["processed"] == 1
    assert result["updated"] == 1
    assert len(fake_repo.calls) == 1
