"""Graders: required facts present and forbidden claims absent for a
summary (strict, and normalised on punctuation and case), the expected
band and category for a score, the expected answer for a resolve pair,
and recall plus the false-positive ceiling for the scrubber."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RUBRIC_VERSION = 1
_NORMALISE = re.compile(r"[^a-z0-9 ]+")


@dataclass
class Result:
    case_id: str
    passed: bool
    xfail: str | None = None
    notes: list[str] = field(default_factory=list)
    strict: bool | None = None


def normalise(text: str) -> str:
    return " ".join(_NORMALISE.sub(" ", text.lower()).split())


def grade_summary(case: dict[str, Any], output: str | None) -> Result:
    result = Result(case["id"], passed=False, xfail=case.get("xfail"))
    if output is None:
        result.notes.append("no output")
        return result
    text = normalise(output)
    missing = [
        fact for fact in case.get("required_facts", []) if normalise(fact) not in text
    ]
    forbidden = [
        claim for claim in case.get("forbidden_claims", []) if normalise(claim) in text
    ]
    too_long = len(output) > int(case.get("max_chars", 600))
    result.strict = all(fact in output for fact in case.get("required_facts", []))
    result.passed = not missing and not forbidden and not too_long
    if missing:
        result.notes.append(f"missing: {', '.join(missing)}")
    if forbidden:
        result.notes.append(f"forbidden: {', '.join(forbidden)}")
    if too_long:
        result.notes.append(f"over {case.get('max_chars', 600)} chars")
    return result


def grade_score(case: dict[str, Any], output: dict[str, Any] | None) -> Result:
    result = Result(case["id"], passed=False, xfail=case.get("xfail"))
    if output is None:
        result.notes.append("no output")
        return result
    lo, hi = case["expected_band"]
    score = output.get("score")
    in_band = isinstance(score, int) and lo <= score <= hi
    category_ok = output.get("category") == case["expected_category"]
    result.passed = in_band and category_ok
    if not in_band:
        result.notes.append(f"score {score} outside {lo}..{hi}")
    if not category_ok:
        result.notes.append(
            f"category {output.get('category')} != {case['expected_category']}"
        )
    return result


def grade_resolve(case: dict[str, Any], output: dict[str, Any] | None) -> Result:
    result = Result(case["id"], passed=False, xfail=case.get("xfail"))
    if output is None:
        result.notes.append("no output")
        return result
    result.passed = bool(output.get("same")) == bool(case["same"])
    if not result.passed:
        result.notes.append(f"same={output.get('same')} expected {case['same']}")
    return result


def grade_case(
    suite: str, case: dict[str, Any], output: str | dict[str, Any] | None
) -> Result:
    if suite == "summaries":
        return grade_summary(case, output if isinstance(output, str) else None)
    if suite == "scoring":
        return grade_score(case, output if isinstance(output, dict) else None)
    return grade_resolve(case, output if isinstance(output, dict) else None)


def grade_scrub(directory: Path) -> list[Result]:
    """Recall over generated identifiers per class and the false-positive
    ceiling over the corpus of real copy."""
    from outception.net.scrub import scrub_report

    from .scrub.generate import generated

    results: list[Result] = []
    for label, samples in generated().items():
        caught = sum(1 for sample in samples if scrub_report(sample).changed)
        recall = caught / len(samples) if samples else 0.0
        results.append(
            Result(
                f"recall:{label}", passed=recall >= 0.98, notes=[f"recall {recall:.3f}"]
            )
        )
    sentences = 0
    flagged = 0
    for path in sorted((directory / "corpus").glob("*.txt")):
        for sentence in re.split(r"(?<=[.!?])\s+", path.read_text()):
            if not sentence.strip():
                continue
            sentences += 1
            if scrub_report(sentence).changed:
                flagged += 1
    rate = flagged / sentences if sentences else 0.0
    results.append(
        Result(
            "false_positives",
            passed=rate <= 0.002,
            notes=[f"{flagged} of {sentences} sentences ({rate:.4f})"],
        )
    )
    return results
