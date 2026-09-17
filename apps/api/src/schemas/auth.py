from collections.abc import Collection

from pydantic import BaseModel, Field

from src.models.entities import User
from src.models.enums import UserRole


class SSOLoginDTO(BaseModel):
    code: str = Field(min_length=1)


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str


class RefreshDTO(BaseModel):
    refreshToken: str = Field(min_length=1)


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    canSudo: bool
    clubIds: list[str]


class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: MeResponse


def user_to_me(user: User, club_ids: Collection[str]) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        canSudo=user.can_sudo,
        clubIds=sorted(club_ids),
    )
