from dataclasses import dataclass
from typing import Any

from fastapi import Header, Request

from src.core.config import Settings, get_settings
from src.core.exceptions import UnauthorizedError


@dataclass(frozen=True)
class AuthContext:
    user_id: str


def _extract_claims_from_event(request: Request) -> dict[str, Any]:
    event = request.scope.get("aws.event", {}) or {}
    request_ctx = event.get("requestContext", {}) or {}
    authorizer = request_ctx.get("authorizer", {}) or {}
    jwt = authorizer.get("jwt", {}) or {}
    claims = jwt.get("claims", {}) or {}
    if isinstance(claims, dict):
        return claims
    return {}


def get_auth_context(
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> AuthContext:
    settings: Settings = get_settings()
    claims = _extract_claims_from_event(request)
    user_id = claims.get("sub")
    if user_id:
        return AuthContext(user_id=str(user_id))

    if settings.allow_insecure_test_auth and x_user_id:
        return AuthContext(user_id=x_user_id)

    raise UnauthorizedError("Valid JWT claims are required")
