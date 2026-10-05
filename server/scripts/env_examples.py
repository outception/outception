"""Fill the production env examples so they load as written.

    python -m scripts.env_examples [--check]

Every typed setting (bool, int, duration, enum, list, map) carries its
default in the examples; only plain strings stay empty, which is where
the secrets and the hosts go. An empty value for a typed field does not
parse, so a `.env.prod` copied from the example and filled with the
secrets alone would stop the server at boot.
"""

import argparse
import json
import re
import sys
from datetime import timedelta
from enum import Enum
from pathlib import Path
from types import NoneType, UnionType
from typing import Union, get_args, get_origin

from outception.config import Settings

SERVER = Path(__file__).parent.parent
EXAMPLES = (
    SERVER / ".env.prod.example",
    SERVER.parent / "deploy" / ".env.prod.example",
)
LINE = re.compile(r"^OUTCEPTION_([A-Z0-9_]+)=$")


def _is_plain_string(annotation: object) -> bool:
    """str, or str | None, or a path: a field whose empty value is its own
    meaning."""
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return False
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        members = [a for a in get_args(annotation) if a is not NoneType]
        return len(members) == 1 and _is_plain_string(members[0])
    return (
        annotation is str
        or annotation is Path
        or (isinstance(annotation, type) and issubclass(annotation, (str, Path)))
    )


def _encode(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, timedelta):
        # The ISO 8601 form the settings parse; bare seconds do not.
        return f"PT{int(value.total_seconds())}S"
    if isinstance(value, (list, set, frozenset, tuple)):
        return json.dumps(
            sorted(value) if isinstance(value, (set, frozenset)) else list(value)
        )
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def default_for(name: str) -> str | None:
    """The example value for a typed field, None for a plain string."""
    field = Settings.model_fields.get(name)
    if field is None or _is_plain_string(field.annotation):
        return None
    if name == "ENV":
        return "production"
    if field.default_factory is not None:
        return _encode(field.default_factory())  # type: ignore[call-arg]
    if field.default is None:
        return None
    return _encode(field.default)


# What the compose stack needs instead of the development default: the
# service names on the internal network, the public addresses, the mounted
# key pair, the production mail sender.
DEPLOY_VALUES = {
    "POSTGRES_HOST": "db",
    "REDIS_HOST": "redis",
    "BASE_URL": "https://api.outception.com",
    "FRONTEND_BASE_URL": "https://outception.com",
    "EMAIL_SENDER": "smtp",
}


def fill(text: str, deploy: bool = False) -> str:
    out = []
    for line in text.splitlines():
        match = LINE.match(line)
        value = default_for(match.group(1)) if match else None
        if match and deploy and match.group(1) in DEPLOY_VALUES:
            value = DEPLOY_VALUES[match.group(1)]
        out.append(f"{line}{value}" if value is not None else line)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="env_examples")
    parser.add_argument(
        "--check", action="store_true", help="fail when an example would change"
    )
    args = parser.parse_args(argv)
    stale = []
    for path in EXAMPLES:
        before = path.read_text()
        after = fill(before, deploy=path.parent.name == "deploy")
        if after != before:
            stale.append(path)
            if not args.check:
                path.write_text(after)
    if args.check and stale:
        print(
            "env_examples: typed settings without a value in "
            + ", ".join(str(p.relative_to(SERVER.parent)) for p in stale)
        )
        return 1
    print(
        "env_examples: "
        + ("up to date" if not stale else f"filled {len(stale)} file(s)")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
