"""Request/response schemas for phone OTP + PIN authentication."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhoneLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone_number: str = Field(..., min_length=8, max_length=20)
    portal: Literal["clinic", "doctor", "pharmacy", "admin"]


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    phone_number: str
    full_name: str
    role: str
    tenant_id: UUID
    clinic_id: UUID | None = None


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
    pin_set: bool = True


class PinSetupRequiredResponse(BaseModel):
    """Returned by /pin/verify when the account has never had a PIN set (first login)."""
    status: Literal["pin_setup_required"] = "pin_setup_required"
    detail: str = "First login detected. Please set your PIN to continue."


class VerifyOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    otp_token: str
    otp_code: str = Field(..., min_length=4, max_length=8, pattern=r"^[0-9]+$")


class VerifyPinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin_token: str
    pin: str = Field(..., min_length=4, max_length=12, pattern=r"^[0-9]+$")


class SetPinRequest(BaseModel):
    """First-login PIN setup. Uses the same pin_token issued after OTP verification."""
    model_config = ConfigDict(extra="forbid")

    pin_token: str
    new_pin: str = Field(..., min_length=4, max_length=12, pattern=r"^[0-9]+$")


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
