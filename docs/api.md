# API Documentation

## Base URL

- Local: `http://localhost:4566/v1`
- AWS: `https://<api-id>.execute-api.<region>.amazonaws.com/dev/v1`

## Authentication

All `/v1/images*` endpoints require one of:

- `Authorization: Bearer <cognito-access-token>` (AWS/Cognito flow)
- `x-user-id: <user-id>` only when `ALLOW_INSECURE_TEST_AUTH=true` (local testing fallback)

If auth is missing/invalid, API returns:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Valid JWT claims are required"
  }
}
```

## Common Metadata Shape

`ImageMetadata` fields returned by image endpoints:

- `image_id` (UUID string)
- `owner_user_id` (string)
- `visibility` (`PUBLIC` or `PRIVATE`)
- `caption` (string or null)
- `tags` (normalized lowercase list)
- `s3_key` (string)
- `content_type` (image mime type)
- `size_bytes` (int)
- `upload_status` (`PENDING_UPLOAD`, `UPLOADED`, `UPLOAD_FAILED`)
- `uploaded_at` (ISO datetime or null)
- `created_at` (ISO datetime)
- `updated_at` (ISO datetime)

## GET /v1/health

Health endpoint (no auth required).

Response `200`:

```json
{
  "status": "ok"
}
```

## POST /v1/images

Creates image metadata and returns a single presigned S3 upload URL.

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

Request field options:

- `caption`: optional, max 2200 chars
- `tags`: optional list, deduplicated + lowercased, max 10 tags, each max 64 chars
- `visibility`: `PUBLIC` or `PRIVATE`
- `content_type`: must match `image/*` and allowed list from config
- `size_bytes`: `> 0` and `<= max_image_size_bytes`
- `file_extension`: alphanumeric extension only

Response `201`:

```json
{
  "image_id": "9d4a44f3-e148-4d8d-a833-9ee82ee81b5c",
  "upload_url": "https://secure-image-service-images.s3.amazonaws.com/images/user/uuid.jpg?...",
  "upload_headers": {
    "Content-Type": "image/jpeg"
  },
  "metadata": {
    "image_id": "9d4a44f3-e148-4d8d-a833-9ee82ee81b5c",
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

Upload rules:

- Upload must be `PUT` to `upload_url`.
- Send `upload_headers` exactly as returned.
- `Content-Type` must match the signed value.
- Do not alter query params in `upload_url`.

## GET /v1/images

Lists caller-owned images.

Query options:

- `visibility`: `PUBLIC` or `PRIVATE` (optional)
- `tag`: tag value (optional, normalized to lowercase)
- `from`: ISO datetime lower bound (optional)
- `to`: ISO datetime upper bound (optional)
- `limit`: `1..100` (default `20`)
- `nextToken`: opaque pagination token from previous response (optional)

Response `200`:

```json
{
  "items": [
    {
      "image_id": "uuid",
      "owner_user_id": "user-sub",
      "visibility": "PUBLIC",
      "caption": "Sunset",
      "tags": ["sunset"],
      "s3_key": "images/user/uuid.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 204800,
      "upload_status": "UPLOADED",
      "uploaded_at": "2026-02-23T11:25:10Z",
      "created_at": "2026-02-23T11:20:10Z",
      "updated_at": "2026-02-23T11:25:10Z"
    }
  ],
  "next_token": "base64-token-or-null"
}
```

Notes:

- With `tag`, API resolves tag edges to image records.
- `next_token` is null when there are no more pages.

## GET /v1/images/{image_id}

Returns one image metadata record.

Access rules:

- owner can always read
- non-owner can read only when `visibility=PUBLIC`

Response `200`: `ImageMetadata`.

Common errors:

- `404` if image does not exist
- `403` if image is private and caller is not owner

## GET /v1/images/{image_id}/download-url

Returns presigned download URL for authorized callers.

Response `200`:

```json
{
  "image_id": "uuid",
  "download_url": "https://secure-image-service-images.s3.amazonaws.com/images/user/uuid.jpg?...",
  "expires_in": 900
}
```

## DELETE /v1/images/{image_id}

Owner-only delete.

Behavior:

- deletes metadata + tag edges from DynamoDB
- deletes image object from S3

Response: `204 No Content`

Common errors:

- `404` if image does not exist
- `403` if caller is not owner

## Error Format

Application errors use:

```json
{
  "error": {
    "code": "bad_request | unauthorized | forbidden | not_found | conflict | internal_error",
    "message": "Human readable message"
  }
}
```
