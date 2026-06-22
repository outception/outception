"""Feedback background tasks.

The Plain support integration was removed with the MoR teardown, so the
"reply in Plain" task is now a no-op kept for enqueue compatibility.
"""

from uuid import UUID

from polar.worker import TaskPriority, actor


@actor(actor_name="feedback.reply_in_plain", priority=TaskPriority.LOW)
async def feedback_reply_in_plain(feedback_id: UUID) -> None:
    return None
