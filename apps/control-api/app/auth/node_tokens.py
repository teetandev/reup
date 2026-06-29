"""Node token generation, prefixing, and hashing.

A node token is issued to a VPS agent when an admin registers a node. It looks
like ``node_live_<random>``. We store only:
- ``node_token_prefix``: the non-secret leading slice, used for display/lookup.
- ``node_token_hash``: an Argon2 hash of the full token.

The plaintext token is shown to the admin **once** (in the install command) and
is never stored, logged, or exposed to the frontend (CLAUDE.md rules 2, 3, 8).
This mirrors ``app/auth/keys.py`` for user secret keys.
"""

from __future__ import annotations

import secrets

from passlib.context import CryptContext

_TOKEN_PREFIX = "node_live_"
# Prefix stored for display/lookup: scheme tag + first 4 chars of the random part.
_PREFIX_LEN = len(_TOKEN_PREFIX) + 4

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def generate_node_token() -> str:
    """Return a new high-entropy node token (plaintext — show once, never store)."""
    return f"{_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def node_token_prefix(token: str) -> str:
    """Return the stored/display prefix for a node token."""
    return token[:_PREFIX_LEN]


def hash_node_token(token: str) -> str:
    """Hash a node token with Argon2 for storage."""
    return _pwd_context.hash(token)


def verify_node_token(token: str, token_hash: str | None) -> bool:
    """Verify a node token against a stored Argon2 hash.

    Returns ``False`` (never raises) on any mismatch or when no hash is stored,
    so callers can treat it as a simple boolean auth check.
    """
    if not token or not token_hash:
        return False
    try:
        return _pwd_context.verify(token, token_hash)
    except Exception:
        return False
