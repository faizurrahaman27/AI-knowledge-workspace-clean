"""
Verifies a Google Sign-In ID token and extracts identity claims.

Requires GOOGLE_CLIENT_ID in .env (a free Google Cloud OAuth Client ID --
see console.cloud.google.com/apis/credentials). Without it, the
/auth/google endpoint returns a clear 400 instead of silently failing.
"""

from fastapi import HTTPException

from src.core.settings import settings


def verify_google_id_token(id_token_str: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="Google Sign-In isn't configured on this server "
            "(GOOGLE_CLIENT_ID missing in backend/.env).",
        )

    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in token.")

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status_code=401, detail="Invalid token issuer.")

    return {
        "sub": claims["sub"],
        "email": claims["email"],
        "full_name": claims.get("name") or claims["email"].split("@")[0],
    }
