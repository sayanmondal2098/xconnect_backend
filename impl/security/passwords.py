from __future__ import annotations

from passlib.context import CryptContext

# bcrypt is a drama queen (72-byte limit, backend detection issues on some stacks).
# PBKDF2-SHA256 is boring and reliable, which is exactly what you want for auth.
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)
