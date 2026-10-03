import uuid
from typing import Annotated

from outception.exceptions import OutceptionTaskError
from outception.integrations.resend.service import resend as resend_service
from outception.observability.task_logging import LoggableField
from outception.worker import AsyncSessionMaker, TaskPriority, actor

from .repository import UserRepository


class UserTaskError(OutceptionTaskError): ...


class UserDoesNotExist(UserTaskError):
    def __init__(self, user_id: uuid.UUID) -> None:
        self.user_id = user_id
        message = f"The user with id {user_id} does not exist."
        super().__init__(message)


@actor(
    actor_name="user.on_after_signup",
    priority=TaskPriority.LOW,
)
async def user_on_after_signup(user_id: Annotated[uuid.UUID, LoggableField]) -> None:
    async with AsyncSessionMaker() as session:
        repository = UserRepository.from_session(session)
        user = await repository.get_by_id(user_id)
        if user is None:
            raise UserDoesNotExist(user_id)
        resend_service.enqueue_sync_user(user.id)
