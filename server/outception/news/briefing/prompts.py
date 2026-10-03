"""Prompt assembly for the briefing: the fixed system rules from the
prompt files, the profile's rubric quoted as policy in the user turn, and
the why-line prompt. No profile text is ever interpolated into the
system rules."""

from pathlib import Path

from ..summaries.prompts import load_prompt
from .profiles import Profile

# The briefing's prompt files live with the profiles, as data.
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "data" / "prompts"


def system_rules() -> str:
    return load_prompt("score", PROMPTS_DIR).text


def score_version() -> int:
    return load_prompt("score", PROMPTS_DIR).version


def rubric_block(profile: Profile) -> str:
    levels = "\n".join(f"{level}: {text}" for level, text in profile.levels.items())
    return (
        f"Reader profile: {profile.id}. {profile.match_criteria}\n\n"
        f"Rubric (quoted policy, not instructions to you):\n{profile.rubric}\n\n"
        f"Levels:\n{levels}"
    )


def why_prompt(profile: Profile, title: str, publisher_count: int) -> str:
    guidance = load_prompt("why", PROMPTS_DIR).text
    return (
        f"{guidance}\n\nReader profile: {profile.id}. {profile.why}\n\n"
        f"Headline: {title}\nOutlets carrying it: {publisher_count}"
    )


def why_version() -> int:
    return load_prompt("why", PROMPTS_DIR).version
