from enum import StrEnum


class TaxBehaviorOption(StrEnum):
    location = "location"
    inclusive = "inclusive"
    exclusive = "exclusive"


class TokenType(StrEnum):
    client_secret = "outception_client_secret"
    client_registration_token = "outception_client_registration_token"
    authorization_code = "outception_authorization_code"
    access_token = "outception_access_token"
    refresh_token = "outception_refresh_token"
    personal_access_token = "outception_personal_access_token"
    organization_access_token = "outception_organization_access_token"
    user_session_token = "outception_user_session_token"


class EmailSender(StrEnum):
    logger = "logger"
    resend = "resend"
    plain = "plain"


class RateLimitGroup(StrEnum):
    web = "web"
    restricted = "restricted"
    default = "default"
    elevated = "elevated"
    pending_auth = "pending_auth"
