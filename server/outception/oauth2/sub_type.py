from enum import StrEnum
from typing import TYPE_CHECKING, Literal, TypeGuard
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from outception.models import User


class SubType(StrEnum):
    user = "user"


SubTypeValue = tuple[SubType, "User"]


def is_sub_user(v: SubTypeValue) -> TypeGuard[tuple[Literal[SubType.user], "User"]]:
    return v[0] == SubType.user


class SubTypeModelMixin:
    sub_type: Mapped[SubType] = mapped_column(String, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="cascade"), nullable=True
    )

    @declared_attr
    def user(cls) -> Mapped["User | None"]:
        return relationship("User", lazy="joined")

    @hybrid_property
    def sub(self) -> "User":
        if self.sub_type != SubType.user:
            raise NotImplementedError()
        if self.user is None:
            raise ValueError("Sub is not found.")
        return self.user

    @sub.inplace.setter
    def _sub_setter(self, value: "User") -> None:
        if self.sub_type != SubType.user:
            raise NotImplementedError()
        self.user_id = value.id

    def get_sub_type_value(self) -> SubTypeValue:
        return self.sub_type, self.sub
