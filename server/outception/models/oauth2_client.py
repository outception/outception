import hmac
from typing import TYPE_CHECKING
from uuid import UUID

from authlib.integrations.sqla_oauth2 import OAuth2ClientMixin
from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from outception.config import settings
from outception.kit.crypto import get_token_hash
from outception.kit.db.models import RateLimitGroupMixin, RecordModel
from outception.oauth2.sub_type import SubType

if TYPE_CHECKING:
    from outception.models import User


class OAuth2Client(RateLimitGroupMixin, RecordModel, OAuth2ClientMixin):
    __tablename__ = "oauth2_clients"
    __table_args__ = (UniqueConstraint("client_id"),)

    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    registration_access_token: Mapped[str] = mapped_column(
        String, index=True, nullable=False
    )
    first_party: Mapped[bool] = mapped_column(nullable=False, default=False)

    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True, index=True
    )

    @declared_attr
    def user(cls) -> "Mapped[User | None]":
        return relationship("User", lazy="raise")

    @staticmethod
    def hash_client_secret(client_secret: str) -> str:
        """Hash a client secret for at-rest storage and comparison
        (HMAC-SHA256), matching how every other credential is stored. The
        plaintext is only ever returned once, at registration."""
        return get_token_hash(client_secret, secret=settings.SECRET)

    def check_client_secret(self, client_secret: str) -> bool:
        """Constant-time verify a presented plaintext secret against the stored
        hash. Overrides the authlib mixin, which compares plaintext-to-plaintext
        (this model stores the hash, so we hash the candidate first)."""
        return hmac.compare_digest(
            self.client_secret, self.hash_client_secret(client_secret)
        )

    @property
    def default_sub_type(self) -> SubType:
        try:
            return SubType(self.client_metadata["default_sub_type"])
        except KeyError:
            return SubType.user
