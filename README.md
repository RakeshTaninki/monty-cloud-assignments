# Secure Image Service (FastAPI + AWS SAM + LocalStack)

Production-grade image metadata service with strict ownership controls, Cognito JWT auth, S3 object storage, and DynamoDB single-table design.

## Features

- FastAPI routes behind API Gateway proxy integration.
- Cognito User Pool JWT authorizer at gateway level.
- Owner-only CRUD + public read of `PUBLIC` images.
- Pre-signed S3 upload/download URLs for scale.
- DynamoDB design with no scans and optimized query access patterns.
- Separate execution workflows for LocalStack and AWS SAM.

## Project Structure

- `src/main.py`: FastAPI app.
- `src/handler.py`: Lambda handler via Mangum.
- `src/api/images.py`: image routes.
- `src/services/`: business logic.
- `src/repositories/`: DynamoDB repository.
- `template.yaml`: infrastructure (SAM).
- `docker-compose.localstack.yml`: LocalStack runtime.
- `scripts/deploy_localstack.sh`: LocalStack deployment helper.
- `scripts/bootstrap_cognito_user.sh`: local Cognito user/token helper.

## Upload Lifecycle

- `POST /v1/images` creates metadata with `upload_status=PENDING_UPLOAD` and returns a presigned `upload_url`.
- Client uploads bytes to S3 using a single presigned `upload_url` and exact `upload_headers`.
- S3 `ObjectCreated` event triggers a Lambda that updates DynamoDB status to `UPLOADED`.
- Check status via `GET /v1/images/{imageId}`.

## Prerequisites

- Python 3.12+
- AWS SAM CLI
- Docker Desktop (for LocalStack)
- AWS CLI v2

## Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
py -m pip install -r requirements-dev.txt
# Optional: specify index URL if using a public PyPI mirror
# py -m pip install -r requirements-dev.txt --index-url https://pypi.org/simple
```

## Option A: Run on LocalStack (Local Environment)

This mode deploys the SAM stack to LocalStack, not to AWS.

1. Start LocalStack:

```bash
docker compose -f docker-compose.localstack.yml up -d
```

2. Set local AWS credentials and endpoint:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-south-1
export AWS_ENDPOINT_URL=http://localhost:4566
```

3. Build and deploy to LocalStack:

```bash
bash scripts/deploy_localstack.sh
```

If you hit `ResourceInUseException` (for example, table already exists), run a clean redeploy:

```bash
CLEAN_LOCALSTACK=true bash scripts/deploy_localstack.sh
```

To verify cleanup manually (same env vars as above):

```bash
aws --endpoint-url http://localhost:4566 --region ap-south-1 dynamodb delete-table --table-name Images
aws --endpoint-url http://localhost:4566 --region ap-south-1 cloudformation delete-stack --stack-name secure-image-service-local
# Wait ~10s, then run deploy again
```

4. (Optional) Create and authenticate a Cognito user in LocalStack:

```bash
bash scripts/bootstrap_cognito_user.sh <user-pool-id> <client-id> <email> <password> http://localhost:4566
```

5. Test with Postman on LocalStack:

- Use this base URL first (from your stack output):
  - `https://unknown.execute-api.amazonaws.com:4566/v1`
  - http://vv847l21xr.execute-api.localhost.localstack.cloud:4566/v1/images
- If TLS/host resolution fails in Postman, use:
  - `http://localhost:4566/v1`
- In Postman, disable SSL certificate verification for LocalStack calls if needed.

LocalStack often returns `unknown` for Cognito/API IDs in stack outputs. For local API testing in this project, use the app-level local auth fallback:

- Add header `x-user-id: user-123` on every request.
- You can skip `Authorization` for local testing with this setup.

Quick Postman requests:

- `GET {{baseUrl}}/health`
- `POST {{baseUrl}}/images`
  - Headers:
    - `Content-Type: application/json`
    - `x-user-id: user-123`
  - Body:
    ```json
    {
      "caption": "Sunset test",
      "tags": ["sunset", "nature"],
      "visibility": "PUBLIC",
      "content_type": "image/jpeg",
      "size_bytes": 204800,
      "file_extension": "jpg"
    }
    ```
- `GET {{baseUrl}}/images` with header `x-user-id: user-123`
- `GET {{baseUrl}}/images/{imageId}` with header `x-user-id: user-123`
- `GET {{baseUrl}}/images/{imageId}/download-url` with header `x-user-id: user-123`
- `DELETE {{baseUrl}}/images/{imageId}` with header `x-user-id: user-123`

Presigned upload requirement:

- Send `PUT` to `upload_url`.
- Include all returned `upload_headers` exactly (especially `Content-Type`).
- Do not alter query params in the URL; otherwise S3 can return `SignatureDoesNotMatch`.

Suggested Postman environment variables:

- `baseUrl` = `http://localhost:4566/v1`
- `userId` = `user-123`

## Option B: Deploy with SAM to AWS (Real Cloud)

This mode deploys to your AWS account. Do not set `AWS_ENDPOINT_URL` for this flow.

1. Configure AWS credentials/profile:

```bash
aws configure
```

2. Build:

```bash
sam build
```

3. Deploy (guided first time):

```bash
sam deploy --guided
```

Suggested parameter values during deploy:
- `AppName`: `secure-image-service`
- `StageName`: `v1`
- `ImagesTableName`: `Images`
- `ImagesBucketName`: globally unique bucket name in your account
- `AllowInsecureTestAuth`: `false`

## API Summary

- `POST /v1/images`
- `GET /v1/images`
- `GET /v1/images/{imageId}`
- `GET /v1/images/{imageId}/download-url`
- `DELETE /v1/images/{imageId}`

Detailed request/response payloads are in `docs/api.md`.

## Testing

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```
