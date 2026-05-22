"""API Key Authentication."""

import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Validate API key from X-API-Key header.

    If API_KEY is not set in env, auth is DISABLED (for local dev).
    If API_KEY is set, every request must include X-API-Key header.
    """
    # No key configured = auth disabled (dev mode)
    if not API_KEY:
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Add header: X-API-Key: YOUR_KEY",
        )

    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
