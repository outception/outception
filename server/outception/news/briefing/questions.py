"""Questions as data: the score, category, route and resolve questions
built from the profile files, so the LLM rendering and the house model's
request body cannot drift."""

from ..summaries.providers.base import Question, QuestionKind
from .profiles import Profile

LEVELS = tuple(str(i) for i in range(11))


def score_questions(profile: Profile) -> list[Question]:
    return [
        Question(
            id="score",
            kind=QuestionKind.score,
            text=f"How important is this story for the {profile.id} profile, 0 to 10?",
            options=LEVELS,
            criteria=dict(profile.levels),
        ),
        Question(
            id="category",
            kind=QuestionKind.choice,
            text="Which category does it belong to?",
            options=profile.category_ids,
            criteria={
                category.id: category.criteria for category in profile.categories
            },
        ),
    ]


def route_question(profiles: list[Profile]) -> Question:
    return Question(
        id="route",
        kind=QuestionKind.choice,
        text="Which reader profile is this story for, or none?",
        options=(*[profile.id for profile in profiles], "none"),
        criteria={
            **{profile.id: profile.match_criteria for profile in profiles},
            "none": "no profile would want it",
        },
    )


def resolve_questions(count: int) -> list[Question]:
    return [
        Question(
            id=f"same_{index}",
            kind=QuestionKind.bool,
            text=f"Are headlines a and b of pair {index} about the same real-world event?",
        )
        for index in range(count)
    ]
