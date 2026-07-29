import uuid

import pytest

from outception.auth import lockout
from outception.redis import Redis


@pytest.mark.asyncio
class TestLockout:
    async def test_locks_after_limit(self, redis: Redis) -> None:
        session_id = str(uuid.uuid4())
        for _ in range(lockout._MAX_FAILURES - 1):
            await lockout.note_failure(redis, session_id)
            assert not await lockout.is_locked(redis, session_id)
        await lockout.note_failure(redis, session_id)
        assert await lockout.is_locked(redis, session_id)
        # Sessions don't share a counter.
        assert not await lockout.is_locked(redis, str(uuid.uuid4()))

    async def test_window_expires(self, redis: Redis) -> None:
        session_id = str(uuid.uuid4())
        await lockout.note_failure(redis, session_id)
        ttl = await redis.ttl(lockout._KEY.format(session_id=session_id))
        assert 0 < ttl <= lockout._WINDOW_SECONDS

    async def test_success_resets(self, redis: Redis) -> None:
        session_id = str(uuid.uuid4())
        for _ in range(lockout._MAX_FAILURES):
            await lockout.note_failure(redis, session_id)
        await lockout.clear(redis, session_id)
        assert not await lockout.is_locked(redis, session_id)
