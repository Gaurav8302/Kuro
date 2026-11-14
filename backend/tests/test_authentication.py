import asyncio
import time
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from security.auth import ClerkJWKSVerifier, get_current_principal


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


@pytest.fixture
def rsa_keypair():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def token(private_key, *, sub="user_A", iss="https://issuer.example", exp=None, nbf=None, aud=None):
    claims = {"sub": sub, "iss": iss, "exp": exp or int(time.time()) + 300}
    if nbf is not None:
        claims["nbf"] = nbf
    if aud is not None:
        claims["aud"] = aud
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "key-1"})


def verifier(public_key):
    instance = ClerkJWKSVerifier.__new__(ClerkJWKSVerifier)
    instance.issuer = "https://issuer.example"
    instance.audience = None
    instance.algorithms = ["RS256"]
    instance._jwks_client = type("Client", (), {"get_signing_key_from_jwt": lambda _self, _token: FakeSigningKey(public_key)})()
    return instance


def test_missing_bearer_token_returns_401():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_principal(None))
    assert exc.value.status_code == 401


def test_valid_clerk_token_returns_verified_principal(rsa_keypair):
    private_key, public_key = rsa_keypair
    principal = verifier(public_key).verify(token(private_key))
    assert principal.user_id == "user_A"
    assert principal.claims["iss"] == "https://issuer.example"


@pytest.mark.parametrize("kwargs", [
    {"exp": int(time.time()) - 60},
    {"iss": "https://attacker.example"},
    {"nbf": int(time.time()) + 600},
])
def test_invalid_claims_rejected(rsa_keypair, kwargs):
    private_key, public_key = rsa_keypair
    with pytest.raises(HTTPException) as exc:
        verifier(public_key).verify(token(private_key, **kwargs))
    assert exc.value.status_code == 401


def test_invalid_signature_rejected(rsa_keypair):
    private_key, _ = rsa_keypair
    from cryptography.hazmat.primitives.asymmetric import rsa

    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as exc:
        verifier(other_private.public_key()).verify(token(private_key))
    assert exc.value.status_code == 401


def test_malformed_token_rejected(rsa_keypair):
    _, public_key = rsa_keypair
    with pytest.raises(HTTPException) as exc:
        verifier(public_key).verify("not.a.jwt")
    assert exc.value.status_code == 401


def test_jwks_unavailable_fails_closed(rsa_keypair):
    private_key, _ = rsa_keypair
    instance = verifier(None)
    instance._jwks_client = type("Client", (), {"get_signing_key_from_jwt": lambda *_args: (_ for _ in ()).throw(RuntimeError("JWKS offline"))})()
    with pytest.raises(HTTPException) as exc:
        instance.verify(token(private_key))
    assert exc.value.status_code == 401


def test_audience_checked_when_configured(rsa_keypair):
    private_key, public_key = rsa_keypair
    instance = verifier(public_key)
    instance.audience = "kuro-api"
    with pytest.raises(HTTPException) as exc:
        instance.verify(token(private_key, aud="another-api"))
    assert exc.value.status_code == 401


def test_admin_role_is_server_allowlist_only():
    from security.auth import AuthenticatedPrincipal, require_admin

    principal = AuthenticatedPrincipal(user_id="user_A", claims={})
    with patch.dict("os.environ", {"ADMIN_USER_IDS": "user_B"}):
        with pytest.raises(HTTPException) as exc:
            require_admin(principal)
    assert exc.value.status_code == 403
