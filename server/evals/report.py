"""One markdown table and one JSON artefact per run."""

from typing import Any

from .grade import RUBRIC_VERSION, Result


def markdown(suite: str, results: list[Result]) -> str:
    passed = sum(1 for r in results if r.passed)
    xfailed = sum(1 for r in results if not r.passed and r.xfail)
    lines = [
        f"## evals: {suite} (rubric v{RUBRIC_VERSION})",
        "",
        f"{passed} of {len(results)} passed, {xfailed} expected failures",
        "",
        "| case | result | notes |",
        "| --- | --- | --- |",
    ]
    for result in results:
        verdict = "pass" if result.passed else ("xfail" if result.xfail else "FAIL")
        if result.strict is not None and result.passed:
            verdict += " (strict)" if result.strict else " (normalised)"
        lines.append(f"| {result.case_id} | {verdict} | {'; '.join(result.notes)} |")
    return "\n".join(lines)


def as_json(suite: str, results: list[Result]) -> dict[str, Any]:
    return {
        "suite": suite,
        "rubric_version": RUBRIC_VERSION,
        "results": [
            {
                "id": r.case_id,
                "passed": r.passed,
                "xfail": r.xfail,
                "strict": r.strict,
                "notes": r.notes,
            }
            for r in results
        ],
    }
