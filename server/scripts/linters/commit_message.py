"""Check a commit message against the naming denylist. Wired as the
`commit-msg` hook; takes the message file path.

    uv run python -m scripts.linters.commit_message .git/COMMIT_EDITMSG
"""

import sys
from pathlib import Path

from .names import DENYLIST, compile_pattern, load_denylist


def check_message(message: str) -> list[str]:
    pattern = compile_pattern(load_denylist(DENYLIST))
    return [
        f"line {lineno}: names {match.group(0)!r}"
        for lineno, line in enumerate(message.splitlines(), start=1)
        if not line.startswith("#") and (match := pattern.search(line)) is not None
    ]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: commit_message <message-file>", file=sys.stderr)
        return 2
    problems = check_message(Path(argv[0]).read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    if problems:
        print("The commit message names a third party; see docs/naming/denylist.txt.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
