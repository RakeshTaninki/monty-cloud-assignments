from __future__ import annotations

from urllib.parse import unquote_plus

from src.models.image import utcnow_iso, validate_image_id
from src.repositories.image_repository import ImageRepository


def parse_s3_key(key: str) -> tuple[str, str] | None:
    decoded = unquote_plus(key)
    parts = decoded.split("/")
    if len(parts) != 3 or parts[0] != "images":
        return None
    owner_user_id = parts[1]
    filename = parts[2]
    if "." not in filename:
        return None
    image_id = filename.rsplit(".", 1)[0]
    try:
        validate_image_id(image_id)
    except ValueError:
        return None
    return owner_user_id, image_id


def lambda_handler(event: dict, _context: object) -> dict[str, int]:
    repository = ImageRepository()
    processed = 0
    updated = 0
    for record in event.get("Records", []):
        if not str(record.get("eventName", "")).startswith("ObjectCreated:"):
            continue
        key = record.get("s3", {}).get("object", {}).get("key", "")
        parsed = parse_s3_key(key)
        if not parsed:
            continue
        owner_user_id, image_id = parsed
        processed += 1
        repository.mark_uploaded(owner_user_id=owner_user_id, image_id=image_id, uploaded_at=utcnow_iso())
        updated += 1
    return {"processed": processed, "updated": updated}
