# API Documentation

All endpoints require a Cognito access token in:

`Authorization: Bearer <token>`

## POST /v1/images

Creates metadata and returns a pre-signed upload URL.

Initial metadata status is `PENDING_UPLOAD`. After successful object upload to S3, the S3 trigger updates it to `UPLOADED`.

Request body:

```json
{
  "caption": "Sunset at beach",
  "tags": ["sunset", "nature"],
  "visibility": "PUBLIC",
  "content_type": "image/jpeg",
  "size_bytes": 204800,
  "file_extension": "jpg"
}
```

Response `201`:

```json
{
  "image_id": "uuid",
  "upload_url": "https://secure-image-service-images.s3.amazonaws.com/images/user/uuid.jpg?...",
  "upload_headers": {
    "Content-Type": "image/jpeg"
  },
  "metadata": {
    "image_id": "uuid",
    "owner_user_id": "user-sub",
    "visibility": "PUBLIC",
    "caption": "Sunset at beach",
    "tags": ["sunset", "nature"],
    "s3_key": "images/user/uuid.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 204800,
    "upload_status": "PENDING_UPLOAD",
    "uploaded_at": null,
    "created_at": "2026-02-22T10:12:01Z",
    "updated_at": "2026-02-22T10:12:01Z"
  }
}
```

Important for presigned upload:

- Upload must be `PUT` to `upload_url` (single URL flow).
- Client must include all `upload_headers` exactly as returned.
- `Content-Type` must match the value used during URL signing.
- Any mismatch can cause `SignatureDoesNotMatch`.

## GET /v1/images

List caller's images (only caller-owned records), with filters:

- `visibility=PUBLIC|PRIVATE`
- `tag=<tag>`
- `from=<ISO8601>`
- `to=<ISO8601>`
- `limit=<1..100>`
- `nextToken=<opaque>`

## GET /v1/images/{imageId}

Returns metadata for:
- owner always
- non-owner only if image visibility is `PUBLIC`

Use this endpoint to verify upload completion:
- `upload_status = PENDING_UPLOAD` before S3 object is written
- `upload_status = UPLOADED` after S3 `ObjectCreated` event processing

## GET /v1/images/{imageId}/download-url

Returns pre-signed URL with short expiry for authorized readers.

## DELETE /v1/images/{imageId}

Owner-only hard delete:
- removes metadata + tag edges from DynamoDB
- removes object from S3
