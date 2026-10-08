"""Lanes: who a model call is for, and what it may spend.

`interactive` is a reader waiting on a summary; `background` is warming,
scoring and resolving. Background never borrows from interactive, and the
warmer stands down when interactive usage passes half its daily cap.
"""

from dataclasses import dataclass
from enum import StrEnum

from outception.config import settings


class Lane(StrEnum):
    interactive = "interactive"
    background = "background"


class Consumer(StrEnum):
    """Background sub-caps, so the resolver cannot starve warming."""

    warm = "warm"
    resolve = "resolve"


@dataclass(frozen=True)
class LaneCaps:
    hourly: int
    daily: int


def caps(lane: Lane) -> LaneCaps:
    if lane == Lane.interactive:
        return LaneCaps(
            settings.LLM_INTERACTIVE_HOURLY_CAP, settings.LLM_INTERACTIVE_DAILY_CAP
        )
    return LaneCaps(
        settings.LLM_BACKGROUND_HOURLY_CAP, settings.LLM_BACKGROUND_DAILY_CAP
    )


def subcap(consumer: Consumer) -> int:
    return {
        Consumer.warm: settings.LLM_BACKGROUND_SUBCAP_WARM,
        Consumer.resolve: settings.LLM_BACKGROUND_SUBCAP_RESOLVE,
    }[consumer]


def warmer_should_stand_down(interactive_daily_used: int) -> bool:
    """The warmer yields the free fleet to readers once interactive usage
    passes half its daily cap."""
    return interactive_daily_used * 2 >= settings.LLM_INTERACTIVE_DAILY_CAP
