from typing import TYPE_CHECKING, Any, cast

from authlib.integrations.sqla_oauth2 import OAuth2TokenMixin
from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from outception.auth.scope import Scope, scope_to_set
from outception.kit.db.models import RecordModel
from outception.oauth2.sub_type import SubTypeModelMixin

if TYPE_CHECKING:
    from .oauth2_client import OAuth2Client


class OAuth2Token(RecordModel, OAuth2TokenMixin, SubTypeModelMixin):
    __tablename__ = "oauth2_tokens"
    __table_args__ = (
        # Supports the `oauth2_token.delete_expired` cron: the expiration is an
        # expression, and the partial predicate leaves out the tokens it can
        # never delete, i.e. those still holding a live refresh token.
        Index(
            "ix_oauth2_tokens_expires_at",
            text("(issued_at + expires_in)"),
            postgresql_where=text(
                "refresh_token IS NULL OR refresh_token_revoked_at != 0"
            ),
        ),
    )

    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[str | None] = mapped_column(String, index=True, nullable=True)

    @declared_attr
    def client(cls) -> "Mapped[OAuth2Client]":
        return relationship(
            "OAuth2Client",
            primaryjoin="foreign(OAuth2Token.client_id) == OAuth2Client.client_id",
            viewonly=True,
            lazy="raise",
        )

    @property
    def expires_at(self) -> int:
        return cast(int, self.issued_at) + cast(int, self.expires_in)

    @property
    def scopes(self) -> set[Scope]:
        return scope_to_set(cast(str, self.get_scope()))

    def get_introspection_data(self, issuer: str) -> dict[str, Any]:
        return {
            "active": not cast(bool, self.is_revoked())
            and not cast(bool, self.is_expired()),
            "client_id": self.client_id,
            "token_type": self.token_type,
            "scope": self.get_scope(),
            "sub_type": self.sub_type,
            "sub": str(self.sub.id),
            "aud": self.client_id,
            "iss": issuer,
            "exp": self.expires_at,
            "iat": self.issued_at,
        }
