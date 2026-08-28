from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models.user import User
from src.core.security import decode_access_token
from src.core.logging import logger

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_access_token(token)

        if payload.get("type") != "access":
            raise credentials_exception

        email = payload.get("sub")
        token_version = payload.get("tv")

        if email is None:
            raise credentials_exception

    except HTTPException:
        raise
    except Exception as e:
        logger.info("JWT validation failed: %s", type(e).__name__)
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()

    if user is None or not user.is_active:
        raise credentials_exception

    if token_version is not None and token_version != user.token_version:
        # Token was issued before a password change / "log out everywhere" --
        # reject it even though its signature and expiry are still valid.
        raise credentials_exception

    return user


def require_roles(*allowed_roles: str):
    """
    Dependency factory for RBAC-protected routes, e.g.:

        @router.get("/admin/users")
        def list_users(user: User = Depends(require_roles("admin"))):
            ...
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return checker
