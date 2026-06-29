"""Secret-key generation, prefixing, and hashing.

A secret key looks like ``sub_live_<random>``. We store only:
- ``key_prefix``: the non-secret leading slice, used to look up candidate keys.
- ``key_hash``: an Argon2 hash of the full key.

The plaintext key is shown to the admin once and never stored or logged.
"""

from __future__ import annotations

import secrets

from passlib.context import CryptContext

_KEY_PREFIX = "sub_live_"
# Prefix stored for lookup/display: scheme tag + first 4 chars of the random part.
_PREFIX_LEN = len(_KEY_PREFIX) + 4

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def generate_secret_key() -> str:
    """Return a new high-entropy secret key (plaintext — show once, never store)."""
    return f"{_KEY_PREFIX}{secrets.token_urlsafe(24)}"


def key_prefix(secret_key: str) -> str:
    """Return the stored/lookup prefix for a secret key."""
    return secret_key[:_PREFIX_LEN]


def hash_key(secret_key: str) -> str:
    """Hash a secret key with Argon2 for storage."""
    return _pwd_context.hash(secret_key)


def verify_key(secret_key: str, key_hash: str) -> bool:
    """Constant-time-ish verify of a secret key against a stored Argon2 hash."""
    try:
        return _pwd_context.verify(secret_key, key_hash)
    except Exception:
        return False
