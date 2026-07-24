from fastapi import Depends
from reauth.factors.oauth2.base import OAuth2Account, OAuth2GetProfileException
from reauth.factors.oauth2.base import OAuth2Enrollment as OAuth2EnrollmentDataclass
from reauth.factors.oauth2.oidc import OIDCException, OIDCFactor

from outception.auth.exceptions import GetEmailError
from outception.config import settings
from outception.postgres import AsyncSession, get_db_session

from .factor import OAuth2FactorMixin
from .state import OAuth2StateService, get_oauth2_state_service


class MicrosoftFactor(OAuth2FactorMixin, OIDCFactor):
    """Sign in with a personal Microsoft account (Outlook / Hotmail / Live /
    Xbox …) via OpenID Connect.

    Uses the ``consumers`` tenant on purpose, NOT ``common``: ``common`` accepts
    a token from any Entra ID tenant, where a tenant admin can set an arbitrary,
    unverified ``email``/``preferred_username`` — the "nOAuth" account-takeover
    class, since we link accounts by email. ``consumers`` only issues tokens for
    Microsoft's personal-accounts tenant (a single fixed issuer), whose email is
    owned and verified by Microsoft, so it can't be spoofed to a victim's
    address.

    References:
        - https://learn.microsoft.com/entra/identity-platform/v2-protocols-oidc
        - nOAuth: https://www.descope.com/blog/post/noauth
    """

    IDENTIFIER = "microsoft"
    SCOPE = ["openid", "email", "profile"]
    DISCOVERY_ENDPOINT = (
        "https://login.microsoftonline.com/consumers/v2.0/.well-known/"
        "openid-configuration"
    )

    def __init__(
        self, session: AsyncSession, state_service: OAuth2StateService
    ) -> None:
        self.session = session
        super().__init__(
            identifier=self.IDENTIFIER,
            state_service=state_service,
            client_id=settings.MICROSOFT_CLIENT_ID,
            client_secret=settings.MICROSOFT_CLIENT_SECRET,
        )

    async def get_email(
        self, callback_result: OAuth2EnrollmentDataclass | OAuth2Account
    ) -> str:
        # Microsoft puts the address in ``email`` when present; personal accounts
        # often only carry it as ``preferred_username`` — fall back to that, and
        # to the userinfo endpoint if the id_token has no usable address. A
        # genuine id_token validation failure surfaces (not silently swallowed).
        if callback_result.id_token is not None:
            try:
                claims = await self.get_id_token_claims(callback_result.id_token)
            except OIDCException as e:
                raise GetEmailError() from e
            email = claims.get("email") or claims.get("preferred_username")
            if email:
                return str(email)

        try:
            profile = await self.get_profile(callback_result.access_token)
        except OAuth2GetProfileException as e:
            raise GetEmailError() from e
        email = profile.get("email") or profile.get("preferred_username")
        if not email:
            raise GetEmailError()
        return str(email)


async def get_microsoft_factor(
    session: AsyncSession = Depends(get_db_session),
    state_service: OAuth2StateService = Depends(get_oauth2_state_service),
) -> MicrosoftFactor:
    return MicrosoftFactor(session, state_service)
