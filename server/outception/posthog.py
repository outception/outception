from __future__ import annotations

from typing import Any

from posthog import Posthog

from outception.config import settings
from outception.logging import ClientContext
from outception.models import User


class Service:
    client: Posthog | None = None

    def configure(self) -> None:
        if not settings.POSTHOG_PROJECT_API_KEY:
            self.client = None
            return

        self.client = Posthog(settings.POSTHOG_PROJECT_API_KEY)
        self.client.disabled = settings.is_testing()
        self.client.debug = settings.POSTHOG_DEBUG
        self.client.feature_enabled

    def capture(
        self,
        distinct_id: str,
        event: str,
        *,
        properties: dict[str, Any] | None = None,
        groups: dict[str, Any] | None = None,
    ) -> None:
        if not self.client:
            return

        self.client.capture(
            event,
            distinct_id=distinct_id,
            groups=groups,
            properties={
                **self._get_common_properties(),
                # Mobile client identification
                **ClientContext.get(),
                **(properties or {}),
            },
        )

    def identify(self, user: User) -> None:
        if not self.client:
            return

        self.client.set(
            distinct_id=user.posthog_distinct_id,
            properties={
                **self._get_common_properties(),
                **self._get_user_properties(user),
            },
        )

    def _get_common_properties(self) -> dict[str, Any]:
        return {
            "_environment": settings.ENV,
        }

    def _get_user_properties(self, user: User) -> dict[str, Any]:
        user_data = {"email": user.email, "verified": user.email_verified}

        signup = {}
        signup_attribution = user.signup_attribution
        if signup_attribution:
            for key, value in signup_attribution.items():
                signup[f"signup_{key}"] = value

        user_data.update(signup)
        return user_data


posthog = Service()


def configure_posthog() -> None:
    posthog.configure()
