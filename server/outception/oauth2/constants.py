from outception.config import settings

from .sub_type import SubType

CLIENT_ID_PREFIX = "outception_ci_"
CLIENT_SECRET_PREFIX = "outception_cs_"
CLIENT_REGISTRATION_TOKEN_PREFIX = "outception_crt_"
AUTHORIZATION_CODE_PREFIX = "outception_ac_"
ACCESS_TOKEN_PREFIX: dict[SubType, str] = {
    SubType.user: "outception_at_u_",
}
REFRESH_TOKEN_PREFIX: dict[SubType, str] = {
    SubType.user: "outception_rt_u_",
}

ISSUER = settings.BASE_URL
SERVICE_DOCUMENTATION = "https://outception.com/docs"
SUBJECT_TYPES_SUPPORTED = ["public"]
ID_TOKEN_SIGNING_ALG = "RS256"
ID_TOKEN_SIGNING_ALG_VALUES_SUPPORTED = [ID_TOKEN_SIGNING_ALG]
ID_TOKEN_EXPIRES_IN = 3600
CLAIMS_SUPPORTED = ["sub", "name", "email", "email_verified"]


def is_registration_token_prefix(value: str) -> bool:
    return value.startswith(CLIENT_REGISTRATION_TOKEN_PREFIX)


def is_access_token_prefix(value: str) -> bool:
    return any(value.startswith(p) for p in ACCESS_TOKEN_PREFIX.values())
