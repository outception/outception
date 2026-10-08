"""Run an eval suite.

    python -m evals.run --suite summaries --saved evals/summaries/saved
    python -m evals.run --suite scoring --saved evals/scoring/saved
    python -m evals.run --suite resolve --saved evals/resolve/saved
    python -m evals.run --suite scrub

`--saved <dir>` re-grades stored model outputs (one `<case id>.txt` or
`.json` per case) with no model call; `--live` runs through the governor
on the background lane under its own small cap. The scrub suite needs
neither: it grades the scrubber itself.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from . import grade, report

ROOT = Path(__file__).resolve().parent
LIVE_CAP = 40


def load_cases(suite: str) -> list[dict[str, Any]]:
    return json.loads((ROOT / suite / "cases.json").read_text())


def saved_output(saved: Path, case_id: str) -> str | dict[str, Any] | None:
    for suffix in (".txt", ".json"):
        path = saved / f"{case_id}{suffix}"
        if path.exists():
            text = path.read_text()
            return json.loads(text) if suffix == ".json" else text
    return None


async def live_summary(case: dict[str, Any]) -> str:
    from bs4 import BeautifulSoup

    from outception.news.summaries.extract import extract_article_text
    from outception.news.summaries.prompts import system_prompt
    from outception.news.summaries.providers.lanes import Lane
    from outception.news.summaries.providers.registry import build_chains
    from outception.redis import create_redis

    html = (ROOT / case["fixture"]).read_text()
    text = extract_article_text(BeautifulSoup(html, "lxml"))
    redis = create_redis("script")
    try:
        reply = await build_chains(redis).generate(
            text, Lane.background, system=system_prompt()
        )
    finally:
        await redis.close()
    return reply.text


async def run(suite: str, saved: Path | None, live: bool) -> int:
    cases = load_cases(suite) if suite != "scrub" else []
    results: list[grade.Result] = []
    if suite == "scrub":
        results = grade.grade_scrub(ROOT / "scrub")
    else:
        if live and len(cases) > LIVE_CAP:
            cases = cases[:LIVE_CAP]
        for case in cases:
            output: str | dict[str, Any] | None
            if live:
                if suite != "summaries":
                    print("live runs exist for summaries only today", file=sys.stderr)  # noqa: T201
                    return 2
                output = await live_summary(case)
            else:
                output = saved_output(saved, case["id"]) if saved else None
            results.append(grade.grade_case(suite, case, output))
    print(report.markdown(suite, results))  # noqa: T201
    (ROOT / f"{suite}.report.json").write_text(
        json.dumps(report.as_json(suite, results), indent=2)
    )
    return 0 if all(r.passed or r.xfail for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals")
    parser.add_argument(
        "--suite", choices=("summaries", "scoring", "resolve", "scrub"), required=True
    )
    parser.add_argument("--saved", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.suite, args.saved, args.live))


if __name__ == "__main__":
    sys.exit(main())
