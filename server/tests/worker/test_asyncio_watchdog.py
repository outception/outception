import logging
import threading
import time
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from dramatiq.asyncio import EventLoopThread

from outception.worker._asyncio import _EventLoopWatchdog


@pytest.fixture
def event_loop_thread() -> Iterator[EventLoopThread]:
    """A dramatiq EventLoopThread running an event loop in the background —
    the same object type the watchdog receives in production."""
    thread = EventLoopThread(logging.getLogger("test-watchdog"))
    thread.start(timeout=2)
    yield thread
    thread.stop()


class TestEventLoopWatchdog:
    def test_healthy_loop_no_dump(self, event_loop_thread: EventLoopThread) -> None:
        with patch.object(_EventLoopWatchdog, "_dump_stacks") as mock_dump:
            watchdog = _EventLoopWatchdog(
                event_loop_thread,
                heartbeat_interval=0.05,
                heartbeat_timeout=0.5,
            )
            watchdog.start()
            time.sleep(0.3)
            watchdog.stop()
            watchdog.join(timeout=2)

            mock_dump.assert_not_called()

    def test_frozen_loop_triggers_dump(
        self, event_loop_thread: EventLoopThread
    ) -> None:
        blocker_started = threading.Event()

        def block_loop() -> None:
            blocker_started.set()
            time.sleep(2)

        event_loop_thread.loop.call_soon_threadsafe(block_loop)
        blocker_started.wait(timeout=1)

        with patch.object(_EventLoopWatchdog, "_dump_stacks") as mock_dump:
            watchdog = _EventLoopWatchdog(
                event_loop_thread,
                heartbeat_interval=0.05,
                heartbeat_timeout=0.3,
            )
            watchdog.start()
            time.sleep(0.6)
            watchdog.stop()
            watchdog.join(timeout=2)

            mock_dump.assert_called()

    def test_stops_cleanly_when_loop_closed(self) -> None:
        thread = EventLoopThread(logging.getLogger("test-watchdog"))
        thread.start(timeout=2)

        watchdog = _EventLoopWatchdog(
            thread, heartbeat_interval=0.05, heartbeat_timeout=0.5
        )
        watchdog.start()
        time.sleep(0.1)

        thread.stop()

        watchdog.join(timeout=2)
        assert not watchdog.is_alive()

    def test_dump_contains_blocking_function_name(
        self, event_loop_thread: EventLoopThread
    ) -> None:
        blocker_started = threading.Event()

        def obviously_blocking_function() -> None:
            blocker_started.set()
            time.sleep(2)

        event_loop_thread.loop.call_soon_threadsafe(obviously_blocking_function)
        blocker_started.wait(timeout=1)

        watchdog = _EventLoopWatchdog(
            event_loop_thread,
            heartbeat_interval=0.05,
            heartbeat_timeout=0.3,
        )

        with patch("outception.worker._asyncio.log") as mock_log:
            watchdog.start()
            time.sleep(0.6)
            watchdog.stop()
            watchdog.join(timeout=2)

            mock_log.error.assert_called()
            call_kwargs = mock_log.error.call_args_list[0][1]
            assert "thread_stacks" in call_kwargs
            assert "obviously_blocking_function" in call_kwargs["thread_stacks"]
            # The targeted event-loop stack is captured by the loop thread's
            # own ident (not a thread name), so it resolves to a real frame.
            assert "event_loop_stack" in call_kwargs
            assert "obviously_blocking_function" in call_kwargs["event_loop_stack"]
            assert "asyncio_tasks" in call_kwargs
            assert "consecutive_misses" in call_kwargs
            assert call_kwargs["consecutive_misses"] >= 1

    def test_consecutive_misses_tracked(
        self, event_loop_thread: EventLoopThread
    ) -> None:
        blocker_started = threading.Event()

        def block_loop() -> None:
            blocker_started.set()
            time.sleep(3)

        event_loop_thread.loop.call_soon_threadsafe(block_loop)
        blocker_started.wait(timeout=1)

        watchdog = _EventLoopWatchdog(
            event_loop_thread,
            heartbeat_interval=0.05,
            heartbeat_timeout=0.3,
        )

        with patch("outception.worker._asyncio.log") as mock_log:
            watchdog.start()
            time.sleep(1.0)
            watchdog.stop()
            watchdog.join(timeout=5)

            error_calls = [
                c
                for c in mock_log.error.call_args_list
                if c[0][0] == "event_loop_unresponsive"
            ]
            assert len(error_calls) >= 2
            assert error_calls[0][1]["consecutive_misses"] == 1
            assert error_calls[1][1]["consecutive_misses"] == 2
