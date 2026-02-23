# API Documentation

All endpoints require a Cognito access token in:

`Authorization: Bearer <token>`

## POST /images

Creates metadata and returns a pre-signed upload URL.

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
  "upload_url": "https://...",
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
    "created_at": "2026-02-22T10:12:01Z",
    "updated_at": "2026-02-22T10:12:01Z"
  }
}
```

## GET /images

List caller's images (only caller-owned records), with filters:

- `visibility=PUBLIC|PRIVATE`
- `tag=<tag>`
- `from=<ISO8601>`
- `to=<ISO8601>`
- `limit=<1..100>`
- `nextToken=<opaque>`

## GET /images/{imageId}

Returns metadata for:
- owner always
- non-owner only if image visibility is `PUBLIC`

## GET /images/{imageId}/download-url

Returns pre-signed URL with short expiry for authorized readers.

## DELETE /images/{imageId}

Owner-only hard delete:
- removes metadata + tag edges from DynamoDB
- removes object from S3
