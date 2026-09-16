from pydantic import BaseModel, Field

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
