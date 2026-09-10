from uuid import UUID

from sqlalchemy import func

from outception.kit.repository import (
    RepositoryBase,
    RepositorySoftDeletionIDMixin,
    RepositorySoftDeletionMixin,
    RepositorySortingMixin,
)
from outception.kit.repository.base import SortingClause
from outception.models import User

from .sorting import UserSortProperty


class UserRepository(
    RepositorySortingMixin[User, UserSortProperty],
    RepositorySoftDeletionIDMixin[User, UUID],
    RepositorySoftDeletionMixin[User],
    RepositoryBase[User],
):
    model = User

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
        included_blocked: bool = False,
    ) -> User | None:
        statement = self.get_base_statement(include_deleted=include_deleted).where(
            func.lower(User.email) == email.lower()
        )
        if not included_blocked:
            statement = statement.where(User.blocked_at.is_(None))
        return await self.get_one_or_none(statement)

    def get_sorting_clause(self, property: UserSortProperty) -> SortingClause:
        match property:
            case UserSortProperty.created_at:
                return self.model.created_at
            case UserSortProperty.email:
                return self.model.email
