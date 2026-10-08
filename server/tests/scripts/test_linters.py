import ast
from pathlib import Path

from scripts.linters import llm_key_boundary
from scripts.linters.commit_message import check_message
from scripts.linters.names import compile_pattern, is_allowed, load_denylist, scan

SERVER = Path(__file__).resolve().parents[1]
REPO = SERVER.parent


class TestNames:
    def test_denylist_loads(self) -> None:
        names = load_denylist()
        assert "hetzner" in names
        assert all("#" not in name for name in names)

    def test_pattern_is_word_bounded(self) -> None:
        pattern = compile_pattern(["acme", "gods-eye-view"])
        assert pattern.search("an Acme product") is not None
        assert pattern.search("acmeware") is None
        assert pattern.search("the gods-eye-view tree") is not None

    def test_allowlist(self) -> None:
        assert is_allowed("server/outception/config.py")
        assert is_allowed("server/outception/news/summaries/providers/governor.py")
        assert not is_allowed("server/outception/news/schemas.py")

    def test_scan_reports_a_planted_name(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "naming").mkdir(parents=True)
        (tmp_path / "docs" / "naming" / "denylist.txt").write_text(
            "acme  # a planted vendor\n"
        )
        (tmp_path / "server" / "outception").mkdir(parents=True)
        (tmp_path / "server" / "x.py").write_text("# built on Acme\nprint(1)\n")
        (tmp_path / "server" / "outception" / "config.py").write_text("ACME = 1\n")
        hits = scan(tmp_path, compile_pattern(["acme"]))
        assert hits == [("server/x.py", 1, "Acme")]

    def test_commit_message(self) -> None:
        assert check_message("Trim the server\n\n# comment mentioning hetzner\n") == []
        assert check_message("Deploy to Hetzner") == ["line 1: names 'Hetzner'"]


class TestKeyBoundary:
    def test_outside_the_governor(self) -> None:
        tree = ast.parse(
            "from outception.config import settings\nkey = settings.GEMINI_API_KEY\n"
        )
        violations = llm_key_boundary.check_with_path(
            tree, Path("outception/news/summaries/service.py")
        )
        assert len(violations) == 1
        assert "GEMINI_API_KEY" in violations[0][1]

    def test_inside_the_governor(self) -> None:
        tree = ast.parse(
            "from outception.config import settings\nkey = settings.GEMINI_API_KEY\n"
        )
        assert (
            llm_key_boundary.check_with_path(
                tree, Path("outception/news/summaries/providers/governor.py")
            )
            == []
        )

    def test_governor_must_not_log_keys(self) -> None:
        tree = ast.parse("log.info('x', api_key=api_key)\nmessage = f'{api_key}'\n")
        violations = llm_key_boundary.check_with_path(
            tree, Path("outception/news/summaries/providers/governor.py")
        )
        assert len(violations) == 2

    def test_other_keys_are_fine_elsewhere(self) -> None:
        tree = ast.parse(
            "from outception.config import settings\nkey = settings.FINNHUB_API_KEY\n"
        )
        assert (
            llm_key_boundary.check_with_path(tree, Path("outception/news/heatmap.py"))
            == []
        )

    def test_the_tree_passes(self) -> None:
        for path in (SERVER / "outception").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            assert llm_key_boundary.check_with_path(tree, path) == [], path
