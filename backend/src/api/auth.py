from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user, require_roles

from src.models.user import User
from src.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenPair,
    LoginResponse,
    RefreshRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    GoogleLoginRequest,
    UpdateThemeRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    TwoFactorSetupResponse,
    TwoFactorConfirmRequest,
    TwoFactorConfirmResponse,
    TwoFactorDisableRequest,
    TwoFactorLoginVerifyRequest,
)
from src.services.auth_service import (
    register_user,
    login_user,
    verify_two_factor_login,
    refresh_access_token,
    logout_everywhere,
    change_password,
    request_password_reset,
    reset_password,
    login_or_register_with_google,
    verify_email,
    resend_verification_email,
    start_two_factor_setup,
    confirm_two_factor_setup,
    disable_two_factor,
)
from src.utils.google_auth import verify_google_id_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    # Public self-registration always creates a "customer" account.
    # Admin/employee accounts are provisioned via the admin-only endpoint below.
    return register_user(db, user, role="customer")


@router.post("/login", response_model=LoginResponse)
def login(
    user: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Returns a normal token pair, OR -- if the account has 2FA enabled --
    `{requires_2fa: true, pending_token: "..."}` instead. The frontend
    must then call POST /auth/2fa/verify-login with that pending_token
    and a code to actually get tokens.
    """
    return login_user(db=db, email=user.email, password=user.password)


@router.post("/token", response_model=TokenPair)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Kept for Swagger UI's built-in "Authorize" button, which requires the
    OAuth2 password-flow form shape rather than a JSON body. NOTE: this
    does not support 2FA -- Swagger's built-in flow has no place to enter
    a code. Use /auth/login + /auth/2fa/verify-login for a 2FA-enabled
    account instead.
    """
    result = login_user(db=db, email=form_data.username, password=form_data.password)
    if result.get("requires_2fa"):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="This account has 2FA enabled -- Swagger's Authorize button can't "
            "complete that flow. Use POST /auth/login then /auth/2fa/verify-login instead.",
        )
    return result


@router.post("/2fa/verify-login", response_model=TokenPair)
def two_factor_verify_login(
    body: TwoFactorLoginVerifyRequest,
    db: Session = Depends(get_db),
):
    return verify_two_factor_login(db, body.pending_token, body.code)


@router.post("/google", response_model=TokenPair)
def google_login(
    body: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    claims = verify_google_id_token(body.id_token)
    return login_or_register_with_google(
        db=db,
        google_sub=claims["sub"],
        email=claims["email"],
        full_name=claims["full_name"],
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    return refresh_access_token(db=db, refresh_token=body.refresh_token)


@router.post("/logout-everywhere")
def logout_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invalidates every access/refresh token issued for this account,
    on every device -- not just the one making this request."""
    logout_everywhere(db, current_user)
    return {"message": "Logged out on all devices."}


@router.post("/change-password", response_model=TokenPair)
def change_my_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_password(db, current_user, body.current_password, body.new_password)


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return request_password_reset(db, body.email)


@router.post("/reset-password")
def do_reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return reset_password(db, body.email, body.token, body.new_password)


@router.post("/verify-email")
def do_verify_email(
    body: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    return verify_email(db, body.email, body.token)


@router.post("/resend-verification")
def do_resend_verification(
    body: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    return resend_verification_email(db, body.email)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def two_factor_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 1 of enabling 2FA: generates a secret + QR provisioning URI.
    Not enabled yet -- call /2fa/confirm with a valid code to finish."""
    return start_two_factor_setup(db, current_user)


@router.post("/2fa/confirm", response_model=TwoFactorConfirmResponse)
def two_factor_confirm(
    body: TwoFactorConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 2: proves the authenticator app was set up correctly, turns
    2FA on, and returns one-time backup codes (shown only once)."""
    return confirm_two_factor_setup(db, current_user, body.code)


@router.post("/2fa/disable")
def two_factor_disable(
    body: TwoFactorDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return disable_two_factor(db, current_user, body.password)


@router.patch("/theme", response_model=UserResponse)
def update_theme(
    body: UpdateThemeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.theme = body.theme
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post("/admin/users", response_model=UserResponse)
def admin_create_user(
    user: UserCreate,
    role: str = "employee",
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    """Admin-only: provision an employee or admin account."""
    return register_user(db, user, role=role)


@router.get("/admin/users/list", response_model=list[UserResponse])
def admin_list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    """Admin-only: list all users, for support and compliance audits."""
    return db.query(User).order_by(User.id.asc()).all()
