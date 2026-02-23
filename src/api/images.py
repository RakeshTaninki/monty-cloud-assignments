from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response

from src.core.security import AuthContext, get_auth_context
from src.models.image import (
    CreateImageRequest,
    CreateImageResponse,
    DownloadUrlResponse,
    ImageMetadata,
    ListImagesQuery,
    ListImagesResponse,
    Visibility,
)
from src.services.image_service import ImageService

router = APIRouter(prefix="/v1/images", tags=["images"])


def get_image_service() -> ImageService:
    return ImageService()


@router.post("", response_model=CreateImageResponse, status_code=201)
def create_image(
    payload: CreateImageRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: ImageService = Depends(get_image_service),
) -> CreateImageResponse:
    return service.create_image(owner_user_id=auth.user_id, payload=payload)


@router.get("", response_model=ListImagesResponse)
def list_images(
    visibility: Visibility | None = Query(default=None),
    tag: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
    next_token: str | None = Query(default=None, alias="nextToken"),
    auth: AuthContext = Depends(get_auth_context),
    service: ImageService = Depends(get_image_service),
) -> ListImagesResponse:
    query = ListImagesQuery(
        visibility=visibility,
        tag=tag,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
        next_token=next_token,
    )
    return service.list_images(caller_user_id=auth.user_id, query=query)


@router.get("/{image_id}", response_model=ImageMetadata)
def get_image(
    image_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: ImageService = Depends(get_image_service),
) -> ImageMetadata:
    return service.get_image(caller_user_id=auth.user_id, image_id=image_id)


@router.get("/{image_id}/download-url", response_model=DownloadUrlResponse)
def get_download_url(
    image_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: ImageService = Depends(get_image_service),
) -> DownloadUrlResponse:
    return service.get_download_url(caller_user_id=auth.user_id, image_id=image_id)


@router.delete("/{image_id}", status_code=204, response_class=Response)
def delete_image(
    image_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: ImageService = Depends(get_image_service),
) -> Response:
    service.delete_image(caller_user_id=auth.user_id, image_id=image_id)
    return Response(status_code=204)
