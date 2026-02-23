#!/usr/bin/env bash
set -euo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-south-1}"

STACK_NAME="${STACK_NAME:-secure-image-service-local}"
APP_NAME="${APP_NAME:-secure-image-service}"
STAGE_NAME="${STAGE_NAME:-v1}"
IMAGES_TABLE_NAME="${IMAGES_TABLE_NAME:-Images}"
IMAGES_BUCKET_NAME="${IMAGES_BUCKET_NAME:-secure-image-service-images-local}"

# Optional cleanup for repeatable LocalStack redeploys.
# Use CLEAN_LOCALSTACK=true to remove failed stack and conflicting table.
# Table is deleted FIRST because in CREATE_FAILED state the table is orphaned (not owned by the stack).
if [[ "${CLEAN_LOCALSTACK:-false}" == "true" ]]; then
  AWS_CMD=(aws --endpoint-url "$AWS_ENDPOINT_URL" --region "$AWS_DEFAULT_REGION")
  
  # Clean build artifacts to ensure fresh template
  echo "[CLEAN] Removing .aws-sam directory..."
  rm -rf .aws-sam

  echo "[CLEAN] Removing table $IMAGES_TABLE_NAME (if exists)..."
  if "${AWS_CMD[@]}" dynamodb describe-table --table-name "$IMAGES_TABLE_NAME" >/dev/null 2>&1; then
    "${AWS_CMD[@]}" dynamodb delete-table --table-name "$IMAGES_TABLE_NAME"
    echo "[CLEAN] Waiting for table deletion..."
    "${AWS_CMD[@]}" dynamodb wait table-not-exists --table-name "$IMAGES_TABLE_NAME" || true
    sleep 2
  else
    echo "[CLEAN] Table $IMAGES_TABLE_NAME not found or already gone."
  fi

  echo "[CLEAN] Removing stack $STACK_NAME (if exists)..."
  if "${AWS_CMD[@]}" cloudformation describe-stacks --stack-name "$STACK_NAME" >/dev/null 2>&1; then
    "${AWS_CMD[@]}" cloudformation delete-stack --stack-name "$STACK_NAME"
    echo "[CLEAN] Waiting for stack deletion..."
    "${AWS_CMD[@]}" cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" || true
    sleep 2
  else
    echo "[CLEAN] Stack $STACK_NAME not found or already gone."
  fi
  echo "[CLEAN] Done. Proceeding to deploy."
fi

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
    AllowInsecureTestAuth=false
