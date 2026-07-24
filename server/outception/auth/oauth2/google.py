from fastapi import Depends
from reauth.factors.oauth2.base import OAuth2Account, OAuth2GetProfileException
from reauth.factors.oauth2.base import OAuth2Enrollment as OAuth2EnrollmentDataclass
from reauth.factors.oauth2.google import GoogleOAuth2Factor as GoogleOAuth2FactorBase

from outception.auth.exceptions import GetEmailError
from outception.config import settings
from outception.postgres import AsyncSession, get_db_session

from .factor import OAuth2FactorMixin
from .state import OAuth2StateService, get_oauth2_state_service


def _is_verified(value: object) -> bool:
    """Google returns email_verified as a bool or the string "true"."""
    return value is True or value == "true"


class GoogleFactor(OAuth2FactorMixin, GoogleOAuth2FactorBase):
    IDENTIFIER = "google"
    SCOPE = ["openid", "email", "profile"]

    def __init__(
        self, session: AsyncSession, state_service: OAuth2StateService
    ) -> None:
        self.session = session
        super().__init__(
            identifier=self.IDENTIFIER,
            state_service=state_service,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

    async def get_email(
        self, callback_result: OAuth2EnrollmentDataclass | OAuth2Account
    ) -> str:
        # Only trust the email for account linking when Google says it verified
        # ownership. Google can issue id_tokens with email_verified=false, and we
        # match/link accounts by email — trusting an unverified address would let
        # someone sign in as a victim whose email they never proved they own.
        if callback_result.id_token is not None:
            try:
                claims = await self.get_id_token_claims(callback_result.id_token)
                if not _is_verified(claims.get("email_verified")):
                    raise GetEmailError()
                return claims["email"]
            except KeyError as e:
                raise GetEmailError() from e

        try:
            profile = await self.get_profile(callback_result.access_token)
            if not _is_verified(profile.get("email_verified")):
                raise GetEmailError()
            return profile["email"]
        except (KeyError, OAuth2GetProfileException) as e:
            raise GetEmailError() from e


async def get_google_factor(
    session: AsyncSession = Depends(get_db_session),
    state_service: OAuth2StateService = Depends(get_oauth2_state_service),
) -> GoogleFactor:
    return GoogleFactor(session, state_service)
