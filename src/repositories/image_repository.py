from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.core.config import Settings, get_settings
from src.models.image import ImageMetadata, ListImagesQuery, UploadStatus, Visibility, utcnow_iso


@dataclass
class ListResult:
    items: list[dict[str, Any]]
    last_evaluated_key: dict[str, Any] | None


def build_image_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def build_image_sk(created_at: str, image_id: str) -> str:
    return f"IMAGE#{created_at}#{image_id}"


def build_tag_sk(tag: str, created_at: str, image_id: str) -> str:
    return f"TAG#{tag}#TS#{created_at}#IMG#{image_id}"


class ImageRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        import boto3

        self.settings = settings or get_settings()
        self._table = boto3.resource("dynamodb", region_name=self.settings.aws_region).Table(
            self.settings.images_table_name
        )
        self._client = boto3.client("dynamodb", region_name=self.settings.aws_region)

    def create_image(self, image: ImageMetadata) -> None:
        created_at = image.created_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
        pk = build_image_pk(image.owner_user_id)
        sk = build_image_sk(created_at, image.image_id)
        gsi2_pk = f"USERVIS#{image.owner_user_id}#{image.visibility.value}"
        gsi2_sk = f"TS#{created_at}#IMG#{image.image_id}"
        now = utcnow_iso()
        expires_at = self._pending_upload_expiry_epoch()

        transact_items: list[dict[str, Any]] = [
            {
                "Put": {
                    "TableName": self.settings.images_table_name,
                    "Item": {
                        "PK": {"S": pk},
                        "SK": {"S": sk},
                        "Type": {"S": "IMAGE"},
                        "imageId": {"S": image.image_id},
                        "ownerUserId": {"S": image.owner_user_id},
                        "visibility": {"S": image.visibility.value},
                        "caption": {"S": image.caption or ""},
                        "tags": {"SS": image.tags or ["_none"]},
                        "s3Key": {"S": image.s3_key},
                        "contentType": {"S": image.content_type},
                        "sizeBytes": {"N": str(image.size_bytes)},
                        "uploadStatus": {"S": image.upload_status.value},
                        "createdAt": {"S": created_at},
                        "updatedAt": {"S": now},
                        "GSI1PK": {"S": f"IMAGE#{image.image_id}"},
                        "GSI1SK": {"S": f"USER#{image.owner_user_id}"},
                        "GSI2PK": {"S": gsi2_pk},
                        "GSI2SK": {"S": gsi2_sk},
                        "expiresAt": {"N": str(expires_at)},
                    },
                    "ConditionExpression": "attribute_not_exists(PK) AND attribute_not_exists(SK)",
                }
            }
        ]
        for tag in image.tags:
            transact_items.append(
                {
                    "Put": {
                        "TableName": self.settings.images_table_name,
                        "Item": {
                            "PK": {"S": pk},
                            "SK": {"S": build_tag_sk(tag, created_at, image.image_id)},
                            "Type": {"S": "TAG_EDGE"},
                            "imageId": {"S": image.image_id},
                            "ownerUserId": {"S": image.owner_user_id},
                            "visibility": {"S": image.visibility.value},
                            "createdAt": {"S": created_at},
                            "imagePK": {"S": pk},
                            "imageSK": {"S": sk},
                            "expiresAt": {"N": str(expires_at)},
                        },
                        "ConditionExpression": "attribute_not_exists(PK) AND attribute_not_exists(SK)",
                    }
                }
            )
        self._client.transact_write_items(TransactItems=transact_items)

    def mark_uploaded(self, owner_user_id: str, image_id: str, uploaded_at: str) -> None:
        from botocore.exceptions import ClientError

        image = self.get_image_by_id(image_id)
        if not image:
            return
        if image.get("ownerUserId") != owner_user_id:
            return
        try:
            self._table.update_item(
                Key={"PK": image["PK"], "SK": image["SK"]},
                UpdateExpression="SET uploadStatus = :uploaded, uploadedAt = :uploadedAt, updatedAt = :updatedAt REMOVE expiresAt",
                ConditionExpression="attribute_not_exists(uploadStatus) OR uploadStatus = :pending",
                ExpressionAttributeValues={
                    ":uploaded": UploadStatus.UPLOADED.value,
                    ":pending": UploadStatus.PENDING_UPLOAD.value,
                    ":uploadedAt": uploaded_at,
                    ":updatedAt": uploaded_at,
                },
            )
            tags: list[str] = list(image.get("tags", []))
            if tags == ["_none"]:
                tags = []
            for tag in tags:
                try:
                    self._table.update_item(
                        Key={
                            "PK": image["PK"],
                            "SK": build_tag_sk(tag, image["createdAt"], image["imageId"]),
                        },
                        UpdateExpression="REMOVE expiresAt",
                        ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
                    )
                except ClientError as tag_exc:
                    if (
                        tag_exc.response.get("Error", {}).get("Code")
                        != "ConditionalCheckFailedException"
                    ):
                        raise
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise

    def _pending_upload_expiry_epoch(self) -> int:
        ttl_seconds = (
            self.settings.presigned_url_expiry_seconds + self.settings.pending_upload_ttl_extra_seconds
        )
        return int(datetime.now(UTC).timestamp()) + ttl_seconds

    def get_image_by_id(self, image_id: str) -> dict[str, Any] | None:
        from boto3.dynamodb.conditions import Key

        response = self._table.query(
            IndexName=self.settings.gsi1_name,
            KeyConditionExpression=Key("GSI1PK").eq(f"IMAGE#{image_id}"),
            Limit=1,
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def list_images(self, user_id: str, query: ListImagesQuery) -> ListResult:
        from boto3.dynamodb.conditions import Key

        exclusive_start_key = query.decode_next_token()
        query_kwargs: dict[str, Any] = {
            "ScanIndexForward": False,
            "Limit": query.limit,
        }
        if exclusive_start_key is not None:
            query_kwargs["ExclusiveStartKey"] = exclusive_start_key

        if query.tag:
            from_ts = (
                query.from_ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
                if query.from_ts
                else "0001-01-01T00:00:00Z"
            )
            to_ts = (
                query.to_ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
                if query.to_ts
                else "9999-12-31T23:59:59Z"
            )
            response = self._table.query(
                KeyConditionExpression=Key("PK").eq(build_image_pk(user_id))
                & Key("SK").between(
                    build_tag_sk(query.tag, from_ts, "00000000-0000-0000-0000-000000000000"),
                    build_tag_sk(query.tag, to_ts, "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"),
                ),
                **query_kwargs,
            )
            edge_items = response.get("Items", [])
            keys = [{"PK": item["imagePK"], "SK": item["imageSK"]} for item in edge_items]
            images: list[dict[str, Any]] = []
            if keys:
                for key in keys:
                    result = self._table.get_item(Key=key)
                    item = result.get("Item")
                    if item:
                        images.append(item)
            image_map = {(item["PK"], item["SK"]): item for item in images}
            ordered = []
            for edge in edge_items:
                found = image_map.get((edge["imagePK"], edge["imageSK"]))
                if found:
                    ordered.append(found)
            return ListResult(
                items=self._apply_visibility_filter(ordered, query.visibility),
                last_evaluated_key=response.get("LastEvaluatedKey"),
            )

        if query.visibility:
            response = self._table.query(
                IndexName=self.settings.gsi2_name,
                KeyConditionExpression=Key("GSI2PK").eq(f"USERVIS#{user_id}#{query.visibility.value}"),
                **query_kwargs,
            )
            return ListResult(
                items=response.get("Items", []), last_evaluated_key=response.get("LastEvaluatedKey")
            )

        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(build_image_pk(user_id))
            & Key("SK").begins_with("IMAGE#"),
            **query_kwargs,
        )
        return ListResult(
            items=response.get("Items", []), last_evaluated_key=response.get("LastEvaluatedKey")
        )

    @staticmethod
    def _apply_visibility_filter(
        items: list[dict[str, Any]], visibility: Visibility | None
    ) -> list[dict[str, Any]]:
        if visibility is None:
            return items
        return [item for item in items if item.get("visibility") == visibility.value]

    def delete_image(self, image: dict[str, Any]) -> None:
        tags: list[str] = list(image.get("tags", []))
        if tags == ["_none"]:
            tags = []
        owner_user_id = image["ownerUserId"]
        image_id = image["imageId"]
        created_at = image["createdAt"]
        pk = build_image_pk(owner_user_id)
        sk = build_image_sk(created_at, image_id)

        transact_items: list[dict[str, Any]] = [
            {
                "Delete": {
                    "TableName": self.settings.images_table_name,
                    "Key": {"PK": {"S": pk}, "SK": {"S": sk}},
                }
            }
        ]
        for tag in tags:
            transact_items.append(
                {
                    "Delete": {
                        "TableName": self.settings.images_table_name,
                        "Key": {"PK": {"S": pk}, "SK": {"S": build_tag_sk(tag, created_at, image_id)}},
                    }
                }
            )
        self._client.transact_write_items(TransactItems=transact_items)


def map_item_to_metadata(item: dict[str, Any]) -> ImageMetadata:
    caption = item.get("caption") or None
    tags = list(item.get("tags", []))
    if tags == ["_none"]:
        tags = []
    return ImageMetadata(
        image_id=item["imageId"],
        owner_user_id=item["ownerUserId"],
        visibility=Visibility(item["visibility"]),
        caption=caption,
        tags=tags,
        s3_key=item["s3Key"],
        content_type=item["contentType"],
        size_bytes=int(item["sizeBytes"]),
        upload_status=UploadStatus(item.get("uploadStatus", UploadStatus.PENDING_UPLOAD.value)),
        uploaded_at=(
            datetime.fromisoformat(item["uploadedAt"].replace("Z", "+00:00"))
            if item.get("uploadedAt")
            else None
        ),
        created_at=datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(item["updatedAt"].replace("Z", "+00:00")),
    )
