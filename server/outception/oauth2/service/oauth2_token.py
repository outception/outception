import time
from typing import cast

import structlog

from outception.email.schemas import OAuth2LeakedTokenEmail, OAuth2LeakedTokenProps
from outception.email.sender import enqueue_email_template
from outception.enums import TokenType
from outception.kit.services import ResourceServiceReader
from outception.logging import Logger
from outception.models import OAuth2Token
from outception.oauth2.repository import OAuth2TokenRepository
from outception.postgres import AsyncSession

log: Logger = structlog.get_logger()


class OAuth2TokenService(ResourceServiceReader[OAuth2Token]):
    async def get_by_access_token(
        self, session: AsyncSession, access_token: str
    ) -> OAuth2Token | None:
        repository = OAuth2TokenRepository.from_session(session)
        token = await repository.get_by_access_token(access_token)

        if token is None:
            return None

        if token.client is None or token.client.is_deleted:
            return None

        if cast(bool, token.is_revoked()):
            return None

        if cast(bool, token.is_expired()):
            return None

        if not token.sub.can_authenticate:
            return None

        return token

    async def delete_expired(self, session: AsyncSession) -> None:
        repository = OAuth2TokenRepository.from_session(session)
        await repository.delete_expired()

    async def revoke_leaked(
        self,
        session: AsyncSession,
        token: str,
        token_type: TokenType,
        *,
        notifier: str,
        url: str | None = None,
    ) -> bool:
        repository = OAuth2TokenRepository.from_session(session)
        oauth2_token = await repository.get_by_leaked_token(token, token_type)

        if oauth2_token is None:
            return False

        if cast(bool, oauth2_token.is_revoked()):
            return True

        # Revoke
        oauth2_token.access_token_revoked_at = int(time.time())  # pyright: ignore
        oauth2_token.refresh_token_revoked_at = int(time.time())  # pyright: ignore
        session.add(oauth2_token)

        # Notify
        recipients: list[str] = [oauth2_token.sub.email]

        oauth2_client = oauth2_token.client

        for recipient in recipients:
            enqueue_email_template(
                OAuth2LeakedTokenEmail(
                    props=OAuth2LeakedTokenProps(
                        email=recipient,
                        client_name=cast(str, oauth2_client.client_name),
                        notifier=notifier,
                        url=url or "",
                    )
                ),
                to_email_addr=recipient,
                subject="Security Notice - Your Outception Access Token has been leaked",
            )

        log.info(
            "Revoke leaked access token and refresh token",
            id=oauth2_token.id,
            token_type=token_type,
            notifier=notifier,
            url=url,
        )

        return True


oauth2_token = OAuth2TokenService(OAuth2Token)
