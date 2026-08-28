from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: int
    name: str
    role: str  # the requesting user's role in this team

    model_config = ConfigDict(from_attributes=True)


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class AcceptInviteRequest(BaseModel):
    email: EmailStr
    token: str


class TeamMemberResponse(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: str


class WorkspaceCreate(BaseModel):
    name: str
    team_id: int | None = None  # None = personal workspace


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int | None = None
    team_id: int | None = None
    document_count: int = 0
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AssignDocumentRequest(BaseModel):
    document_id: int
