#!/usr/bin/env bash
set -euo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-south-1}"

STACK_NAME="${STACK_NAME:-secure-image-service-local}"
APP_NAME="${APP_NAME:-secure-image-service}"
STAGE_NAME="${STAGE_NAME:-v1}"
IMAGES_TABLE_NAME="${IMAGES_TABLE_NAME:-Images}"
IMAGES_BUCKET_NAME="${IMAGES_BUCKET_NAME:-secure-image-service-images}"

sam build
sam deploy \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --resolve-s3 \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    AppName="$APP_NAME" \
    StageName="$STAGE_NAME" \
    ImagesTableName="$IMAGES_TABLE_NAME" \
    ImagesBucketName="$IMAGES_BUCKET_NAME" \
    S3AddressingStyle=auto \
    AllowInsecureTestAuth=false
