"""Centralized Clerk JWT verification and server-controlled authorization."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    claims: dict[str, Any]


def _derive_clerk_domain() -> str:
    """Extract the Clerk instance domain from a publishable key (pk_test_... or pk_live_...)."""
    pk = os.getenv("CLERK_PUBLISHABLE_KEY") or os.getenv("VITE_CLERK_PUBLISHABLE_KEY") or ""
    if pk.startswith("pk_test_") or pk.startswith("pk_live_"):
        parts = pk.split("_")
        if len(parts) >= 3:
            raw = parts[2]
            pad = len(raw) % 4
            if pad:
                raw += "=" * (4 - pad)
            try:
                import base64
                decoded = base64.b64decode(raw).decode("utf-8").rstrip("$")
                if "." in decoded:
                    return decoded
            except Exception:
                pass
    return ""


class ClerkJWKSVerifier:
    """Verify Clerk-issued JWTs against a cached, rotating JWKS key set."""

    def __init__(self) -> None:
        self.issuer = (os.getenv("CLERK_JWT_ISSUER") or os.getenv("CLERK_ISSUER") or "").rstrip("/")
        self.jwks_url = os.getenv("CLERK_JWKS_URL", "")
        self.audience = os.getenv("CLERK_JWT_AUDIENCE") or None

        # Auto-derive from publishable key if missing or set to placeholder
        if not self.issuer or "your-instance" in self.issuer:
            derived_domain = _derive_clerk_domain()
            if derived_domain:
                self.issuer = f"https://{derived_domain}"
        if not self.jwks_url or "your-instance" in self.jwks_url:
            if self.issuer and "your-instance" not in self.issuer:
                self.jwks_url = f"{self.issuer}/.well-known/jwks.json"

        if not self.issuer or not self.jwks_url:
            raise RuntimeError("Clerk JWT issuer and JWKS URL must be configured")
        self.algorithms = ["RS256"]
        self._jwks_client = PyJWKClient(
            self.jwks_url,
            cache_jwk_set=True,
            lifespan=int(os.getenv("CLERK_JWKS_CACHE_SECONDS", "3600")),
            cache_keys=True,
            timeout=float(os.getenv("CLERK_JWKS_TIMEOUT_SECONDS", "5")),
        )

    def verify(self, token: str) -> AuthenticatedPrincipal:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=self.algorithms,
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["sub", "iss", "exp"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": self.audience is not None,
                },
            )
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject.strip():
                raise jwt.InvalidTokenError("Missing subject")
            return AuthenticatedPrincipal(user_id=subject, claims=claims)
        except Exception as exc:
            # Never expose whether the key, signature, claims, or token was wrong.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


# Test mode: when TESTING=1 and DISABLE_MEMORY_INIT=1, use local test JWKS
_TEST_MODE = os.getenv("TESTING") == "1" and os.getenv("DISABLE_MEMORY_INIT") == "1"

# Fixed test key pair - defined at module level for access by get_test_* functions
_fixed_test_private_key = None
_fixed_test_public_key = None

if _TEST_MODE:
    from cryptography.hazmat.primitives.asymmetric import rsa
    _fixed_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _fixed_test_public_key = _fixed_test_private_key.public_key()

# Export fixed test key pair for conftest to use
def set_test_public_key(public_key):
    """Override the test public key used for JWT verification in test mode."""
    global _fixed_test_public_key
    _fixed_test_public_key = public_key


def get_test_private_key():
    """Return the fixed test private key for token signing in tests."""
    return _fixed_test_private_key


def get_test_public_key():
    """Return the fixed public key for verification in tests."""
    return _fixed_test_public_key


if _TEST_MODE:
    _test_private_key = _fixed_test_private_key
    _test_public_key = _fixed_test_public_key

    _test_jwks = {
        "keys": [{
            "kty": "RSA",
            "kid": "test-key-1",
            "use": "sig",
            "alg": "RS256",
            "n": _fixed_test_public_key.public_numbers().n,
            "e": _fixed_test_public_key.public_numbers().e,
        }]
    }

    class _TestVerifier:
        issuer = "https://test-clerk.example"
        audience = "kuro-api"
        algorithms = ["RS256"]
        def verify(self, token: str) -> AuthenticatedPrincipal:
            try:
                claims = jwt.decode(
                    token,
                    _fixed_test_public_key,
                    algorithms=self.algorithms,
                    issuer=self.issuer,
                    audience=self.audience,
                    options={
                        "require": ["sub", "iss", "exp"],
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_nbf": True,
                        "verify_iss": True,
                        "verify_aud": self.audience is not None,
                    },
                )
                subject = claims.get("sub")
                if not isinstance(subject, str) or not subject.strip():
                    raise jwt.InvalidTokenError("Missing subject")
                return AuthenticatedPrincipal(user_id=subject, claims=claims)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc

    def _get_verifier() -> ClerkJWKSVerifier:
        return _TestVerifier()
else:
    @lru_cache(maxsize=1)
    def _get_verifier() -> ClerkJWKSVerifier:
        try:
            return ClerkJWKSVerifier()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not configured",
            ) from exc


async def get_current_principal(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> AuthenticatedPrincipal:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, credential = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credential.strip() or " " in credential.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _get_verifier().verify(credential.strip())


def require_admin(principal: AuthenticatedPrincipal = Depends(get_current_principal)) -> AuthenticatedPrincipal:
    """Authorize only user IDs listed in a server-controlled deployment setting."""
    allowed_ids = {
        item.strip()
        for item in os.getenv("ADMIN_USER_IDS", "").split(",")
        if item.strip()
    }
    if principal.user_id not in allowed_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return principal


def require_service_token(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_metrics_token: Optional[str] = Header(default=None, alias="X-Metrics-Token"),
) -> None:
    """Protect metrics for trusted scrapers using a dedicated secret."""
    import hmac

    expected = os.getenv("METRICS_BEARER_TOKEN", "")
    supplied = x_metrics_token or ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
