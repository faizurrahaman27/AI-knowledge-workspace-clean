from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_two_factor_pending_token,
    decode_two_factor_pending_token,
    decode_refresh_token,
    generate_reset_token,
    hash_reset_token,
    VALID_ROLES,
)
from src.core.settings import settings
from src.core.logging import logger
from src.models.user import User
from src.schemas.user import UserCreate
from src.utils.email import send_password_reset_email, send_verification_email
from src.utils.totp import (
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp_code,
    generate_backup_codes,
    hash_backup_codes,
    consume_backup_code,
)


def _utc_now() -> datetime:
    """
    Naive UTC datetime, deliberately not timezone-aware. SQLite has no
    real datetime type -- it stores whatever we hand it and hands back a
    naive datetime on read, so comparing against an aware datetime.now()
    raises TypeError. Keeping everything naive-but-UTC throughout this
    module avoids that mismatch. (If you switch to Postgres, this still
    works fine -- Postgres just stores it as a naive timestamp too unless
    the column type says otherwise.)
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_user(db: Session, user: UserCreate, role: str = "customer"):

    if role not in VALID_ROLES:
        role = "customer"

    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(user.password)

    new_user = User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed,
        role=role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("New user registered: user_id=%s role=%s", new_user.id, new_user.role)

    _send_verification_email(db, new_user)

    return new_user


def _send_verification_email(db: Session, user: User):
    raw_token, hashed_token = generate_reset_token()  # same secure-random pattern, different purpose
    user.verification_token_hash = hashed_token
    user.verification_token_expires = _utc_now() + timedelta(hours=24)
    db.commit()

    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}&email={user.email}"
    send_verification_email(user.email, verify_link)


def resend_verification_email(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    # Same anti-enumeration behavior as password reset -- don't reveal
    # whether the email exists.
    if user and not user.email_verified:
        _send_verification_email(db, user)
    return {"message": "If that email is registered and unverified, a new link has been sent."}


def verify_email(db: Session, email: str, raw_token: str):
    user = db.query(User).filter(User.email == email).first()

    invalid = HTTPException(status_code=400, detail="Invalid or expired verification link.")

    if not user or not user.verification_token_hash or not user.verification_token_expires:
        raise invalid
    if user.verification_token_expires < _utc_now():
        raise invalid
    if hash_reset_token(raw_token) != user.verification_token_hash:
        raise invalid

    user.email_verified = 1
    user.verification_token_hash = None
    user.verification_token_expires = None
    db.commit()

    logger.info("Email verified: user_id=%s", user.id)

    return {"message": "Email verified."}


def _issue_tokens(user: User) -> dict:
    return {
        "access_token": create_access_token(subject=user.email, role=user.role, token_version=user.token_version),
        "refresh_token": create_refresh_token(subject=user.email, token_version=user.token_version),
        "token_type": "bearer",
    }


def _is_locked(user: User) -> bool:
    return bool(user.locked_until and user.locked_until > _utc_now())


def login_user(db: Session, email: str, password: str):

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        if user:
            _register_failed_attempt(db, user)
        logger.info("Failed login attempt for email=%s", email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    if _is_locked(user):
        minutes_left = int((user.locked_until - _utc_now()).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=423,
            detail=f"Too many failed attempts. Try again in {minutes_left} minute(s).",
        )

    # Successful login resets the failed-attempt counter.
    if user.failed_login_attempts:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()

    if user.totp_enabled:
        # Correct password, but not done yet -- prove the second factor
        # before any real token is issued. The pending token only proves
        # "this request knew the password"; it grants no API access.
        logger.info("Login requires 2FA: user_id=%s", user.id)
        return {
            "requires_2fa": True,
            "pending_token": create_two_factor_pending_token(subject=user.email),
        }

    logger.info("User logged in: user_id=%s", user.id)

    return _issue_tokens(user)


def verify_two_factor_login(db: Session, pending_token: str, code: str):
    try:
        payload = decode_two_factor_pending_token(pending_token)
    except Exception:
        raise HTTPException(status_code=401, detail="2FA session expired. Please log in again.")

    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user or not user.totp_enabled:
        raise HTTPException(status_code=401, detail="Invalid 2FA session.")

    if verify_totp_code(user.totp_secret, code):
        logger.info("2FA login verified via TOTP: user_id=%s", user.id)
        return _issue_tokens(user)

    # Fall back to a backup code -- single use, consumed on success.
    updated_hashes = consume_backup_code(user.totp_backup_codes_hash, code)
    if updated_hashes is not None:
        user.totp_backup_codes_hash = updated_hashes
        db.commit()
        logger.info("2FA login verified via backup code: user_id=%s", user.id)
        return _issue_tokens(user)

    logger.info("Failed 2FA code attempt: user_id=%s", user.id)
    raise HTTPException(status_code=401, detail="Invalid authentication code.")


def _register_failed_attempt(db: Session, user: User):
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

    if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = _utc_now() + timedelta(minutes=settings.LOCKOUT_MINUTES)
        logger.info("Account locked due to repeated failed logins: user_id=%s", user.id)

    db.commit()


def refresh_access_token(db: Session, refresh_token: str):
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    if payload.get("tv") != user.token_version:
        raise HTTPException(status_code=401, detail="This refresh token has been revoked.")

    return _issue_tokens(user)


def logout_everywhere(db: Session, user: User):
    """Invalidates every previously issued access/refresh token for this
    user by bumping token_version -- no token blacklist table needed."""
    user.token_version += 1
    db.commit()
    logger.info("Logged out everywhere: user_id=%s", user.id)


def change_password(db: Session, user: User, current_password: str, new_password: str):
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    user.hashed_password = hash_password(new_password)
    user.token_version += 1  # invalidate all other sessions on password change
    db.commit()
    logger.info("Password changed: user_id=%s", user.id)

    return _issue_tokens(user)  # fresh tokens for the session that just changed it


def request_password_reset(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()

    # Always behave the same whether or not the email exists, so this
    # endpoint can't be used to enumerate registered accounts.
    if user:
        raw_token, hashed_token = generate_reset_token()
        user.reset_token_hash = hashed_token
        user.reset_token_expires = _utc_now() + timedelta(minutes=30)
        db.commit()

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}&email={email}"
        send_password_reset_email(email, reset_link)

    return {"message": "If that email is registered, a reset link has been sent."}


def reset_password(db: Session, email: str, raw_token: str, new_password: str):
    user = db.query(User).filter(User.email == email).first()

    invalid = HTTPException(status_code=400, detail="Invalid or expired reset link.")

    if not user or not user.reset_token_hash or not user.reset_token_expires:
        raise invalid

    if user.reset_token_expires < _utc_now():
        raise invalid

    if hash_reset_token(raw_token) != user.reset_token_hash:
        raise invalid

    user.hashed_password = hash_password(new_password)
    user.reset_token_hash = None
    user.reset_token_expires = None
    user.token_version += 1  # invalidate any sessions from before the reset
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    logger.info("Password reset completed: user_id=%s", user.id)

    return {"message": "Password has been reset. You can now log in."}


def login_or_register_with_google(db: Session, google_sub: str, email: str, full_name: str):
    user = db.query(User).filter(User.google_sub == google_sub).first()

    if not user:
        # Link to an existing email/password account if one matches,
        # otherwise create a new Google-only account (no password).
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_sub = google_sub
        else:
            user = User(
                full_name=full_name,
                email=email,
                hashed_password=None,
                google_sub=google_sub,
                role="customer",
                email_verified=1,  # Google already verified this address
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    logger.info("User logged in via Google: user_id=%s", user.id)

    return _issue_tokens(user)


# --- Two-factor authentication setup ------------------------------------

def start_two_factor_setup(db: Session, user: User):
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled.")

    # Generate (or regenerate) an unconfirmed secret -- not enabled until
    # the user proves they can generate a valid code from it.
    secret = generate_totp_secret()
    user.totp_secret = secret
    db.commit()

    return {
        "secret": secret,
        "otpauth_url": get_provisioning_uri(secret, user.email),
    }


def confirm_two_factor_setup(db: Session, user: User, code: str):
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="Start 2FA setup first.")
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled.")

    if not verify_totp_code(user.totp_secret, code):
        raise HTTPException(status_code=400, detail="Incorrect code. Check your authenticator app and try again.")

    backup_codes = generate_backup_codes()
    user.totp_backup_codes_hash = hash_backup_codes(backup_codes)
    user.totp_enabled = 1
    user.token_version += 1  # invalidate old sessions issued before 2FA existed
    db.commit()

    logger.info("2FA enabled: user_id=%s", user.id)

    return {"backup_codes": backup_codes}


def disable_two_factor(db: Session, user: User, password: str):
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    user.totp_enabled = 0
    user.totp_secret = None
    user.totp_backup_codes_hash = None
    user.token_version += 1
    db.commit()

    logger.info("2FA disabled: user_id=%s", user.id)

    return {"message": "Two-factor authentication disabled."}
