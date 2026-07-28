"""
Password hashing helpers (bcrypt via passlib).

Never store plain-text passwords. Always store password_hash.
"""

from __future__ import annotations

from passlib.context import CryptContext

# bcrypt is the industry default for password hashes.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain password for storage in users.password_hash."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    if not plain_password or not password_hash:
        return False
    return _pwd_context.verify(plain_password, password_hash)
