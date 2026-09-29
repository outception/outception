"""Failed-attempt lockout for one-time codes (email OTP, TOTP, backup codes).

The codes are short and their verify endpoints were otherwise free to
brute-force within the code's lifetime. Wrong codes are counted per
authentication session; past the limit every further attempt in the window is
rejected with the same error a wrong code gets, so a locked session can't be
told apart from a mistyped one.
"""

from outception.redis import Redis

_KEY = "auth:lockout:{session_id}"
_WINDOW_SECONDS = 15 * 60
_MAX_FAILURES = 5


async def is_locked(redis: Redis, session_id: str) -> bool:
    failures = await redis.get(_KEY.format(session_id=session_id))
    return int(failures or 0) >= _MAX_FAILURES


async def note_failure(redis: Redis, session_id: str) -> None:
    key = _KEY.format(session_id=session_id)
    if await redis.incr(key) == 1:
        await redis.expire(key, _WINDOW_SECONDS)


async def clear(redis: Redis, session_id: str) -> None:
    await redis.delete(_KEY.format(session_id=session_id))
