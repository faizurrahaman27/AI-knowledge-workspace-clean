"""
Minimal email sending, used only for password-reset links.

If SMTP isn't configured (the common case for local/dev use, and for this
sandbox where no real SMTP credentials exist), the "email" is logged to
the server console instead of sent -- the app stays fully usable, you
just copy the link from the logs rather than your inbox. Configure
SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM_EMAIL in .env for real
delivery before a real launch.
"""

import smtplib
from email.message import EmailMessage

from src.core.settings import settings
from src.core.logging import logger


def send_verification_email(to_email: str, verify_link: str) -> None:
    if not settings.SMTP_HOST:
        logger.info(
            "SMTP not configured -- email verification link for %s: %s",
            to_email, verify_link,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = "Verify your email"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.set_content(
        f"Click the link below to verify your email address. This link expires in 24 hours.\n\n{verify_link}\n\n"
        "If you didn't create this account, you can safely ignore this email."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        logger.exception("Failed to send verification email to %s", to_email)
        logger.info("Fallback -- email verification link for %s: %s", to_email, verify_link)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if not settings.SMTP_HOST:
        logger.info(
            "SMTP not configured -- password reset link for %s: %s",
            to_email, reset_link,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.set_content(
        f"Click the link below to reset your password. This link expires in 30 minutes.\n\n{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        # Don't leak SMTP errors to the client -- log the link as a fallback
        # so the user isn't completely stuck.
        logger.info("Fallback -- password reset link for %s: %s", to_email, reset_link)
