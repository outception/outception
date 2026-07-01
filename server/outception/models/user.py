from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from reauth.factors.oauth2.base import OAuth2Enrollment as OAuth2EnrollmentDataclass
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    ColumnElement,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    and_,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from outception.kit.db.models import RecordModel
from outception.kit.extensions.sqlalchemy.types import StringEnum
from outception.kit.schemas import Schema


class OAuthPlatform(StrEnum):
    # maximum allowed length is 32 chars
    github = "github"
    google = "google"
    apple = "apple"


class IdentityVerificationStatus(StrEnum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    failed = "failed"

    def get_display_name(self) -> str:
        return {
            IdentityVerificationStatus.unverified: "Unverified",
            IdentityVerificationStatus.pending: "Pending",
            IdentityVerificationStatus.verified: "Verified",
            IdentityVerificationStatus.failed: "Failed",
        }[self]


class OAuthAccount(RecordModel):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "account_id",
        ),
        Index("idx_user_id_platform", "user_id", "platform"),
    )

    platform: Mapped[OAuthPlatform] = mapped_column(String(32), nullable=False)
    access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    refresh_token: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )
    refresh_token_expires_at: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    account_id: Mapped[str] = mapped_column(String(320), nullable=False)
    account_email: Mapped[str] = mapped_column(String(320), nullable=False)
    account_username: Mapped[str | None] = mapped_column(String(320), nullable=True)

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="cascade"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

    def to_dataclass(self, scope: list[str]) -> OAuth2EnrollmentDataclass:
        return OAuth2EnrollmentDataclass(
            id=self.id,
            provider=self.platform,
            scope=scope,
            access_token=self.access_token,
            expires_at=self.expires_at,
            refresh_token=self.refresh_token,
            refresh_token_expires_at=self.refresh_token_expires_at,
            account_id=self.account_id,
            identity_id=self.user_id,
        )


class User(RecordModel):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_email_case_insensitive", func.lower(Column("email")), unique=True
        ),
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    @declared_attr
    def oauth_accounts(cls) -> Mapped[list[OAuthAccount]]:
        return relationship(OAuthAccount, lazy="joined", back_populates="user")

    accepted_terms_of_service_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=None,
    )
    accepted_terms_of_service_ip: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        default=None,
    )

    @hybrid_property
    def accepted_terms_of_service(self) -> bool:
        return self.accepted_terms_of_service_at is not None

    identity_verification_status: Mapped[IdentityVerificationStatus] = mapped_column(
        StringEnum(IdentityVerificationStatus),
        nullable=False,
        default=IdentityVerificationStatus.unverified,
    )
    identity_verification_id: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None, unique=True
    )

    @property
    def identity_verified(self) -> bool:
        return self.identity_verification_status == IdentityVerificationStatus.verified

    # Time of blocking traffic/activity for given user
    blocked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=None,
    )

    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    promotion_emails_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    first_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, default=None)
    date_of_birth: Mapped[date | None] = mapped_column(
        Date, nullable=True, default=None
    )

    @hybrid_property
    def can_authenticate(self) -> bool:
        return not self.is_deleted and self.blocked_at is None

    @can_authenticate.inplace.expression
    @classmethod
    def _can_authenticate_expression(cls) -> ColumnElement[bool]:
        return and_(cls.is_deleted.is_(False), cls.blocked_at.is_(None))

    @property
    def signup_attribution(self) -> dict[str, Any]:
        return self.meta.get("signup", {})

    @signup_attribution.setter
    def signup_attribution(self, value: dict[str, Any] | Schema | None) -> None:
        if not value:
            return

        meta = self.meta or {}
        if isinstance(value, Schema):
            value = value.model_dump(exclude_unset=True)

        meta["signup"] = value
        self.meta = meta

    @property
    def posthog_distinct_id(self) -> str:
        return f"user:{self.id}"
