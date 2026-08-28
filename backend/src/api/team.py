from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.schemas.team import (
    TeamCreate, TeamResponse, InviteMemberRequest, AcceptInviteRequest,
    TeamMemberResponse,
)
from src.services.team_service import (
    create_team, list_my_teams, invite_member, accept_invite, list_team_members,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("/", response_model=TeamResponse)
def create(
    body: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = create_team(db, body.name, current_user)
    return {"id": team.id, "name": team.name, "role": "owner"}


@router.get("/", response_model=list[TeamResponse])
def list_mine(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        {"id": item["team"].id, "name": item["team"].name, "role": item["role"]}
        for item in list_my_teams(db, current_user)
    ]


@router.post("/{team_id}/invite")
def invite(
    team_id: int,
    body: InviteMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return invite_member(db, team_id, current_user, body.email, body.role)


@router.post("/accept-invite")
def accept(
    body: AcceptInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return accept_invite(db, body.email, body.token, current_user)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
def members(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_team_members(db, team_id, current_user)
