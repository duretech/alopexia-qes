"""Request/response schemas for phone OTP + PIN authentication."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhoneLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone_number: str = Field(..., min_length=8, max_length=20)
    portal: Literal["doctor", "pharmacy", "admin"]


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    phone_number: str
    full_name: str
    role: str
    tenant_id: UUID


class AuthenticatedResponse(BaseModel):
    status: Literal["authenticated"] = "authenticated"
    token: str
    user: AuthUserResponse


class OtpRequiredResponse(BaseModel):
    status: Literal["otp_required"] = "otp_required"
    otp_token: str
    otp_expires_in_seconds: int
    otp_debug: str | None = None


class PinRequiredResponse(BaseModel):
    status: Literal["pin_required"] = "pin_required"
    pin_token: str


class VerifyOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    otp_token: str
    otp_code: str = Field(..., min_length=4, max_length=8, pattern=r"^[0-9]+$")


class VerifyPinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin_token: str
    pin: str = Field(..., min_length=4, max_length=12, pattern=r"^[0-9]+$")


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
