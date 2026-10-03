import typing
from collections.abc import Iterable

from pydantic import UUID4, EmailStr, Field
from reauth.authentication_session import (
    AuthenticationSession as AuthenticationSessionDataclass,
)
from reauth.factors import FactorBase

from outception.kit.http import ReturnTo
from outception.kit.schemas import Schema

# The login method recorded in the `outception_last_login_method` cookie.
LoginMethod = typing.Literal[
    "email_otp", "totp", "backup_codes", "apple", "google", "microsoft"
]


class BaseFactor(Schema):
    type: typing.Literal[
        "email_otp", "totp", "backup_codes", "apple", "google", "microsoft"
    ]


Factor = BaseFactor


def _factor_to_schema(factor: FactorBase[typing.Any]) -> BaseFactor:
    return BaseFactor.model_validate({"type": factor.identifier})


class AuthenticationSessionStart(Schema):
    return_to: ReturnTo | None = None


class GlobalAuthenticationSessionStart(AuthenticationSessionStart):
    pass


class AuthenticationSession(Schema):
    identity_id: UUID4 | None
    available_factors: list[Factor]

    @classmethod
    def from_session_and_factors(
        cls,
        authentication_session: AuthenticationSessionDataclass,
        factors: Iterable[FactorBase[typing.Any]],
    ) -> typing.Self:
        return cls(
            identity_id=authentication_session.identity_id,
            available_factors=[_factor_to_schema(factor) for factor in factors],
        )


class EmailOTPRequest(Schema):
    email: EmailStr
    turnstile_token: str = Field(alias="cf-turnstile-response")


class EmailOTPVerify(Schema):
    code: str


class TOTPEnrollment(Schema):
    secret: str
    algorithm: str
    digits: int
    period: int
    provisioning_uri: str


class TOTPStatus(Schema):
    enabled: bool


class TOTPEnable(Schema):
    code: str


class TOTPVerify(Schema):
    code: str


class BackupCodesEnrollment(Schema):
    codes: list[str]


class BackupCodesVerify(Schema):
    code: str


class BackupCodesStatus(Schema):
    codes: int
    used_codes: int
