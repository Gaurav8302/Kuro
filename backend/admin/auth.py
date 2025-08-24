"""Admin authentication utilities (Step 6)."""
from __future__ import annotations
import os
from fastapi import Header, HTTPException, status

ADMIN_HEADER = "X-Admin-Key"


def verify_admin(x_admin_key: str = Header(None)):
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin key not configured")
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")
    return True

__all__ = ["verify_admin", "ADMIN_HEADER"]
