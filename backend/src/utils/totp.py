"""
TOTP (Time-based One-Time Password) two-factor authentication -- the same
mechanism Google Authenticator, Authy, and 1Password's TOTP feature all
implement (RFC 6238). No external service or API key needed; this is
pure math + a shared secret, verified locally.
"""

import hashlib
import secrets

import pyotp

APP_NAME = "Production RAG Chatbot"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str) -> str:
    """
    The otpauth:// URI that authenticator apps scan as a QR code. The
    frontend renders this into an actual QR code client-side (no need to
    generate an image server-side).
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=APP_NAME)


def verify_totp_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    # valid_window=1 tolerates the code from one 30s step before/after,
    # which absorbs normal clock drift between the user's phone and the
    # server without meaningfully weakening the window an attacker gets.
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Human-typeable one-time codes, e.g. for when the user's phone is
    lost. Returned once to the user; only hashes are ever stored."""
    return ["-".join([secrets.token_hex(2), secrets.token_hex(2)]) for _ in range(count)]


def hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


def hash_backup_codes(codes: list[str]) -> str:
    return ",".join(hash_backup_code(c) for c in codes)


def consume_backup_code(stored_hashes_csv: str, submitted_code: str) -> str | None:
    """
    Returns the updated (hash removed) CSV string if the code was valid
    and unused, or None if it didn't match anything -- backup codes are
    single-use, so a valid match must be removed from the stored list.
    """
    if not stored_hashes_csv:
        return None

    hashes = stored_hashes_csv.split(",")
    target = hash_backup_code(submitted_code)

    if target not in hashes:
        return None

    hashes.remove(target)
    return ",".join(hashes)
