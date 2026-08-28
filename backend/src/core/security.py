import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from src.core.settings import settings

VALID_ROLES = {"admin", "employee", "customer"}

# bcrypt's algorithm hard-caps input at 72 bytes; passing more raises an
# error rather than truncating for you. Encode + truncate explicitly here
# so a long (but otherwise valid) password never 500s.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_prepare(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False  # Google-only account with no password set
    try:
        return bcrypt.checkpw(_prepare(password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str, token_version: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject, "role": role, "tv": token_version,
        "type": "access", "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_two_factor_pending_token(subject: str) -> str:
    """
    Issued right after a correct password but BEFORE a valid 2FA code --
    proves "this request knows the password" without granting any real
    access. Deliberately short-lived and a distinct `type` so it can never
    be mistaken for (or reused as) an access token even if it leaked.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": subject, "type": "2fa_pending", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_two_factor_pending_token(token: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "2fa_pending":
        raise ValueError("Not a 2FA pending token.")
    return payload


def create_refresh_token(subject: str, token_version: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject, "tv": token_version,
        "type": "refresh", "exp": expire,
    }
    return jwt.encode(
        payload, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(
        token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
    )


# --- Password reset tokens ---------------------------------------------
# Store only a hash of the reset token in the DB (like a password), so a
# DB leak alone doesn't hand out working reset links. The raw token is
# what actually goes in the emailed/logged link.

def generate_reset_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
