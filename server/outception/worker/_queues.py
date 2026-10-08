from enum import IntEnum, StrEnum


class TaskPriority(IntEnum):
    HIGH = 0
    MEDIUM = 50
    LOW = 100


class TaskQueue(StrEnum):
    HIGH_PRIORITY = "high_priority"
    MEDIUM_PRIORITY = "medium_priority"
    LOW_PRIORITY = "low_priority"
    # The news pipeline (cluster, score, build, prune, the live-signal and
    # weather pollers) runs on its own queue so a burst never sits ahead of
    # the warmer on the shared low queue.
    NEWS_PIPELINE = "news_pipeline"


__all__ = [
    "TaskPriority",
    "TaskQueue",
]
