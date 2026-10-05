"""Every env example must load into the settings as written: a value that
cannot parse (an empty string where a list is expected) would stop a
fresh checkout or a fresh deploy before the first request."""

from pathlib import Path

import pytest

from outception.config import Settings

SERVER = Path(__file__).parent.parent
EXAMPLES = [
    SERVER / ".env.example",
    SERVER / ".env.prod.example",
    SERVER.parent / "deploy" / ".env.prod.example",
]


@pytest.mark.parametrize(
    "example", EXAMPLES, ids=[str(p.relative_to(SERVER.parent)) for p in EXAMPLES]
)
def test_example_loads(
    example: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Only the file: a value in the test process environment must not mask
    # a broken line in the example.
    for key in list(__import__("os").environ):
        if key.startswith("OUTCEPTION_"):
            monkeypatch.delenv(key)
    # A production example leaves the secret empty on purpose; the one
    # value a deploy must bring is the one the test supplies.
    monkeypatch.setenv(
        "OUTCEPTION_SECRET", "a-strong-unique-value-for-the-test-" + "x" * 32
    )
    # The dev example points at the built email renderer, which a fresh
    # checkout and CI do not have; the file only has to exist.
    renderer = tmp_path / "renderer"
    renderer.touch()
    monkeypatch.setenv("OUTCEPTION_EMAIL_RENDERER_BINARY_PATH", str(renderer))
    settings = Settings(_env_file=example)
    assert isinstance(settings.ADMIN_EMAILS, list)
    assert isinstance(settings.BRIEFING_PROFILES, list)
