"""Request/response schemas for portal login and MFA."""

from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # NOTE: We intentionally do NOT use EmailStr here because email-validator
    # rejects special-use/reserved TLDs like ".local", which we use for dev seeds.
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(default="", min_length=0, max_length=500)
    portal: Literal["doctor", "pharmacy", "admin"]


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    full_name: str
    role: str
    tenant_id: UUID


class LoginAuthenticated(BaseModel):
    status: Literal["authenticated"] = "authenticated"
    token: str
    user: AuthUserResponse


class LoginMfaRequired(BaseModel):
    status: Literal["mfa_required"] = "mfa_required"
    mfa_token: str


class LoginMfaEnrollment(BaseModel):
    status: Literal["mfa_enrollment"] = "mfa_enrollment"
    enrollment_token: str
    otpauth_uri: str


LoginResponse = Annotated[
    Union[LoginAuthenticated, LoginMfaRequired, LoginMfaEnrollment],
    Field(discriminator="status"),
]


class MfaVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mfa_token: str
    code: str = Field(..., min_length=6, max_length=8, pattern=r"^[0-9]+$")


class MfaCompleteEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_token: str
    code: str = Field(..., min_length=6, max_length=8, pattern=r"^[0-9]+$")


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
