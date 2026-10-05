"""The naming rule: no third party is named outside the allowlisted paths.

Reads `docs/naming/denylist.txt` (one name per line, `#` comments) and scans
every text file under the tree for the names, case-insensitive on word
boundaries. Reports every hit with its path and line. Exit 0 unless
`--strict`, which fails on any hit: reporting mode until the known copy
violations are fixed, then the gate.

    uv run python -m scripts.linters.names [--strict] [--root DIR] [PATH ...]
"""

import argparse
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DENYLIST = REPO / "docs" / "naming" / "denylist.txt"

# Paths where vendor identifiers have to exist: provider modules, the env
# contract, deploy files, manifests, the integration modules kept for logs
# and backups, the error reporter, and recorded live data.
ALLOWED_PATHS: tuple[str, ...] = (
    "server/outception/news/summaries/providers/",
    "server/outception/news/heatmap/providers/",
    "server/outception/news/briefing/providers/",
    "server/outception/news/heatmap/specs.py",
    "server/outception/config.py",
    "server/.env.prod.example",
    "server/.env.example",
    "server/.env.testing",
    "server/outception/integrations/",
    "server/outception/email/sender.py",
    "server/outception/enums.py",
    "server/outception/auth/turnstile.py",
    "server/outception/kit/http.py",
    "server/outception/kit/hash_secrets.py",
    "server/outception/kit/jwk.py",
    "server/outception/kit/aws.py",
    "server/outception/sentry.py",
    "server/outception/logfire.py",
    "server/outception/observability/",
    "server/scripts/linters/",
    "server/scripts/check_env_vars.py",
    "server/tests/news/fixtures/parity/",
    "server/tests/cards/fixtures/",
    # Publishers and data sources are content, and the catalog is where they
    # are named.
    "server/outception/news/data/",
    # The tests of the allowlisted modules name what those modules name.
    "server/tests/news/summaries/",
    "server/tests/news/briefing/test_push.py",
    "server/tests/news/test_summary.py",
    "server/tests/auth/test_turnstile.py",
    "server/tests/integrations/",
    "server/tests/kit/test_aws.py",
    "server/tests/kit/test_hash_secrets.py",
    "server/tests/kit/test_http.py",
    "server/tests/kit/test_signer.py",
    "server/tests/scripts/test_linters.py",
    "server/tests/health/test_service.py",
    "server/pyproject.toml",
    "server/uv.lock",
    "server/Dockerfile",
    "server/docker-compose.yml",
    "deploy/",
    "docs/naming/",
    ".github/",
    "clients/scripts/check-names.ts",
    # The licence text carries the original copyright notice as the law asks.
    "LICENSE",
    # The web build config carries the content security policy's host list.
    "clients/apps/web/next.config.mjs",
    # The crawler manifest names crawlers by their user agents.
    "clients/apps/web/src/app/robots.ts",
    # The installer has to know where each coding agent keeps its config.
    "clients/packages/cli/src/targets.ts",
)
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".claude",
        ".agents",
        ".editor",
        ".next",
        "dist",
        "build",
        ".turbo",
        "bin",
    }
)
SKIP_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".pdf",
        ".zip",
        ".mmdb",
        ".lock",
        ".pyc",
        ".svg",
        ".mp4",
    }
)
SKIP_NAMES = frozenset({"pnpm-lock.yaml", "package-lock.json", "yarn.lock", "uv.lock"})
# The planning documents under plans/ and the session log are git-excluded
# and may name anything; that is why they are skipped.
SKIP_RELATIVE = (
    "plans/",
    ".agents-sync.md",
    ".agents/",
)


def load_denylist(path: Path = DENYLIST) -> list[str]:
    names: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            names.append(line)
    return names


def compile_pattern(names: Iterable[str]) -> re.Pattern[str]:
    alternatives = "|".join(
        re.escape(name) for name in sorted(names, key=len, reverse=True)
    )
    return re.compile(
        rf"(?<![A-Za-z0-9_])(?:{alternatives})(?![A-Za-z0-9_])", re.IGNORECASE
    )


def is_allowed(relative: str) -> bool:
    return any(relative.startswith(prefix) for prefix in ALLOWED_PATHS)


def iter_files(root: Path, paths: list[Path] | None = None) -> Iterator[Path]:
    starts = paths or [root]
    for start in starts:
        if start.is_file():
            yield start
            continue
        for path in sorted(start.rglob("*")):
            if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                continue
            if (
                not path.is_file()
                or path.suffix in SKIP_SUFFIXES
                or path.name in SKIP_NAMES
            ):
                continue
            yield path


def scan(
    root: Path, pattern: re.Pattern[str], paths: list[Path] | None = None
) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in iter_files(root, paths):
        relative = path.relative_to(root).as_posix()
        if is_allowed(relative):
            continue
        if any(relative == skip or relative.startswith(skip) for skip in SKIP_RELATIVE):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = pattern.search(line)
            if match is not None:
                hits.append((relative, lineno, match.group(0)))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="fail on any hit")
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    pattern = compile_pattern(load_denylist(root / "docs" / "naming" / "denylist.txt"))
    paths = [
        (root / p).resolve() if not p.is_absolute() else p for p in args.paths
    ] or None
    hits = scan(root, pattern, paths)
    for relative, lineno, name in hits:
        print(f"{relative}:{lineno}: names {name!r}")
    if hits:
        print(f"\n{len(hits)} hit(s) outside the allowlisted paths.")
        return 1 if args.strict else 0
    print("OK: no third party named outside the allowlisted paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
