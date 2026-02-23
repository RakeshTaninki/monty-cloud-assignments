#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "Usage: $0 <user-pool-id> <client-id> <email> <password> <endpoint-url>"
  exit 1
fi

USER_POOL_ID="$1"
CLIENT_ID="$2"
EMAIL="$3"
PASSWORD="$4"
ENDPOINT_URL="$5"

aws --endpoint-url "$ENDPOINT_URL" cognito-idp sign-up \
  --client-id "$CLIENT_ID" \
  --username "$EMAIL" \
  --password "$PASSWORD"

aws --endpoint-url "$ENDPOINT_URL" cognito-idp admin-confirm-sign-up \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL"

aws --endpoint-url "$ENDPOINT_URL" cognito-idp initiate-auth \
  --client-id "$CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME="$EMAIL",PASSWORD="$PASSWORD"
