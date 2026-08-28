from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.team import Team, TeamMembership, TeamInvite, TEAM_ROLES
from src.models.user import User
from src.core.security import generate_reset_token, hash_reset_token
from src.core.settings import settings
from src.core.logging import logger
from src.utils.email import send_password_reset_email  # reused generic SMTP-or-log sender


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _send_invite_email(to_email: str, link: str, team_name: str):
    # Reuses the same "log if no SMTP configured" sender as password
    # reset -- it's generic (subject/body agnostic to the caller), just
    # named after its original use case.
    from src.core.settings import settings
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured -- team invite link for %s: %s", to_email, link)
        return
    send_password_reset_email(to_email, link)  # good enough for dev; real product would have its own template


def create_team(db: Session, name: str, owner: User) -> Team:
    team = Team(name=name)
    db.add(team)
    db.commit()
    db.refresh(team)

    db.add(TeamMembership(team_id=team.id, user_id=owner.id, role="owner"))
    db.commit()

    logger.info("Team created: team_id=%s owner_id=%s", team.id, owner.id)
    return team


def get_membership(db: Session, team_id: int, user_id: int) -> TeamMembership | None:
    return (
        db.query(TeamMembership)
        .filter(TeamMembership.team_id == team_id, TeamMembership.user_id == user_id)
        .first()
    )


def require_team_role(db: Session, team_id: int, user: User, allowed_roles: set[str]) -> TeamMembership:
    membership = get_membership(db, team_id, user.id)
    if not membership or membership.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="You don't have permission to do that in this team.")
    return membership


def list_my_teams(db: Session, user: User):
    memberships = db.query(TeamMembership).filter(TeamMembership.user_id == user.id).all()
    return [
        {"team": m.team, "role": m.role}
        for m in memberships
    ]


def invite_member(db: Session, team_id: int, inviter: User, email: str, role: str):
    require_team_role(db, team_id, inviter, {"owner", "admin"})

    if role not in TEAM_ROLES:
        role = "member"

    raw_token, hashed_token = generate_reset_token()

    invite = TeamInvite(
        team_id=team_id,
        email=email,
        role=role,
        token_hash=hashed_token,
        expires_at=_utc_now() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()

    team = db.query(Team).filter(Team.id == team_id).first()
    link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}&email={email}"
    _send_invite_email(email, link, team.name)

    return {"message": f"Invite sent to {email}."}


def accept_invite(db: Session, email: str, raw_token: str, user: User):
    invite = (
        db.query(TeamInvite)
        .filter(TeamInvite.email == email, TeamInvite.accepted == 0)
        .order_by(TeamInvite.id.desc())
        .first()
    )

    invalid = HTTPException(status_code=400, detail="Invalid or expired invite.")

    if not invite:
        raise invalid
    if invite.expires_at < _utc_now():
        raise invalid
    if hash_reset_token(raw_token) != invite.token_hash:
        raise invalid
    if user.email != email:
        raise HTTPException(status_code=403, detail="This invite was sent to a different email address.")

    existing = get_membership(db, invite.team_id, user.id)
    if not existing:
        db.add(TeamMembership(team_id=invite.team_id, user_id=user.id, role=invite.role))

    invite.accepted = 1
    db.commit()

    logger.info("Team invite accepted: team_id=%s user_id=%s", invite.team_id, user.id)

    team = db.query(Team).filter(Team.id == invite.team_id).first()
    return {"message": f"Joined {team.name}.", "team_id": invite.team_id}


def remove_member(db: Session, team_id: int, remover: User, member_user_id: int):
    require_team_role(db, team_id, remover, {"owner", "admin"})

    membership = get_membership(db, team_id, member_user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found.")
    if membership.role == "owner":
        raise HTTPException(status_code=400, detail="Can't remove the team owner.")

    db.delete(membership)
    db.commit()
    return {"message": "Member removed."}


def list_team_members(db: Session, team_id: int, requester: User):
    # Any member can view the roster; only owner/admin can invite/remove.
    if not get_membership(db, team_id, requester.id):
        raise HTTPException(status_code=403, detail="You're not a member of this team.")

    memberships = db.query(TeamMembership).filter(TeamMembership.team_id == team_id).all()
    return [
        {
            "user_id": m.user.id,
            "full_name": m.user.full_name,
            "email": m.user.email,
            "role": m.role,
        }
        for m in memberships
    ]
