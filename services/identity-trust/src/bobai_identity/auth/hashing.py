"""Password hashing with Argon2id (OWASP-recommended).

Passwords are NEVER stored in plaintext or reversibly. We store only the Argon2id
hash (which embeds its own random salt + parameters). Verification is constant-time
and supports transparent rehashing when parameters are upgraded.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Argon2id with sensible interactive parameters.
_ph = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)


def hash_password(password: str) -> str:
    """Return an Argon2id hash string (salt + params embedded)."""
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """Constant-time verification. Returns False on mismatch or malformed hash."""
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True
