"""Fail when the env contract and the settings disagree.

`.env.prod.example` is the contract: every `OUTCEPTION_*` name an operator
has to know about. Every name there must be a field of `Settings`, and every
field of `Settings` must appear there, so a setting never goes unprovisioned
and a provisioned value is never silently ignored (`extra="allow"` means the
app itself would not complain).

Exit codes follow the linter convention: 0 clean, 1 drift found, 2 the check
itself failed. Run it from `server/`:

    uv run python -m scripts.check_env_vars
"""

import ast
import re
import sys
import traceback
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
CONFIG = SERVER / "outception" / "config.py"
CONTRACT = SERVER / ".env.prod.example"

NAME = re.compile(r"^\s*(?:export\s+)?(OUTCEPTION_[A-Z0-9_]+)\s*=", re.MULTILINE)

# Fields that are read from the environment but intentionally absent from the
# contract: development-only switches nobody sets in production.
INTERNAL: frozenset[str] = frozenset(
    {
        "OUTCEPTION_TESTING",
        "OUTCEPTION_SQLALCHEMY_DEBUG",
        "OUTCEPTION_LOCAL_JWKS",
        "OUTCEPTION_LOCAL_JWK_KID",
        "OUTCEPTION_ENCRYPTION_LOCAL_KEY",
        "OUTCEPTION_EMAIL_RENDERER_BINARY_PATH",
        "OUTCEPTION_WORKER_PROMETHEUS_DIR",
        "OUTCEPTION_POSTGRES_URL_NON_POOLING",
        "OUTCEPTION_REDIS_URL",
    }
)


def contract() -> set[str]:
    if not CONTRACT.exists():
        raise RuntimeError(f"{CONTRACT} is missing")
    return set(NAME.findall(CONTRACT.read_text()))


def fields() -> set[str]:
    tree = ast.parse(CONFIG.read_text())
    settings = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "Settings"
        ),
        None,
    )
    if settings is None:
        raise RuntimeError(f"No Settings class in {CONFIG}")
    return {
        f"OUTCEPTION_{statement.target.id}"
        for statement in settings.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and not statement.target.id.startswith("_")
        and statement.target.id.isupper()
    }


def main() -> int:
    declared = contract()
    read = fields()
    unknown = declared - read
    missing = read - declared - INTERNAL
    if not unknown and not missing:
        print(f"OK: {len(declared)} OUTCEPTION_* names agree with the settings.")
        return 0
    if unknown:
        print(f"{len(unknown)} name(s) in {CONTRACT.name} that no setting reads:")
        for name in sorted(unknown):
            print(f"  {name}")
    if missing:
        print(f"{len(missing)} setting(s) missing from {CONTRACT.name}:")
        for name in sorted(missing):
            print(f"  {name}")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # 2 separates "the check broke" from "the check found something".
        traceback.print_exc()
        sys.exit(2)
