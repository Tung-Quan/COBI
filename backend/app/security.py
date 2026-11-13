from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .db import LOCAL_USER_ID

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=300)


def require_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    auth_base_url = os.environ.get("NEON_AUTH_BASE_URL", "").rstrip("/")
    jwks_url = os.environ.get("NEON_AUTH_JWKS_URL", "")

    if not auth_base_url and not jwks_url:
        if os.environ.get("DATABASE_URL"):
            raise HTTPException(status_code=503, detail="Authentication is not configured for this workspace.")
        return LOCAL_USER_ID
    if not auth_base_url or not jwks_url:
        raise HTTPException(status_code=503, detail="Authentication is not configured for this workspace.")
    parsed_auth_url = urlsplit(auth_base_url)
    if parsed_auth_url.scheme not in {"http", "https"} or not parsed_auth_url.netloc:
        raise HTTPException(status_code=503, detail="Authentication is not configured for this workspace.")
    # Neon Auth's base URL includes its auth path, while its JWT issuer is the URL origin.
    issuer = f"{parsed_auth_url.scheme}://{parsed_auth_url.netloc}"
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to access your workspace.",
                            headers={"WWW-Authenticate": "Bearer"})

    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["EdDSA"],
            issuer=issuer,
            options={"require": ["sub", "exp", "iss"], "verify_aud": False},
        )
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise jwt.InvalidTokenError("Missing subject")
        return subject
    except (jwt.PyJWTError, ValueError, OSError) as exc:
        raise HTTPException(status_code=401, detail="Your session is invalid or has expired.",
                            headers={"WWW-Authenticate": "Bearer"}) from exc
