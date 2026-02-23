from src.core.config import Settings, get_settings


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        import boto3

        self.settings = settings or get_settings()
        self._client = boto3.client("s3", region_name=self.settings.aws_region)

    def build_s3_key(self, owner_user_id: str, image_id: str, file_extension: str) -> str:
        ext = file_extension.lower().lstrip(".")
        return f"images/{owner_user_id}/{image_id}.{ext}"

    def create_upload_url(self, s3_key: str, content_type: str) -> tuple[str, dict[str, str]]:
        url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.settings.images_bucket_name,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=self.settings.presigned_url_expiry_seconds,
            HttpMethod="PUT",
        )
        return url, {"Content-Type": content_type}

    def create_download_url(self, s3_key: str) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.settings.images_bucket_name,
                "Key": s3_key,
            },
            ExpiresIn=self.settings.presigned_url_expiry_seconds,
            HttpMethod="GET",
        )

    def delete_object(self, s3_key: str) -> None:
        self._client.delete_object(Bucket=self.settings.images_bucket_name, Key=s3_key)
