import json
from pathlib import Path

import pytest

from outception.news.briefing import profiles as profiles_module
from outception.news.briefing.profiles import ProfileError, load_profile, load_profiles
from outception.news.briefing.questions import (
    resolve_questions,
    route_question,
    score_questions,
)
from outception.news.briefing.router import by_sources, needs_route_question


class TestLoader:
    def test_the_shipped_profiles_load(self) -> None:
        loaded = load_profiles()
        assert set(loaded) >= {"developer", "investor", "sports", "news-junkie"}
        developer = loaded["developer"]
        assert developer.template == "developer"
        assert "hackernews" in developer.sources
        assert "heatmap-tech" in developer.sources
        assert set(developer.levels) == {str(i) for i in range(11)}
        assert developer.match_criteria
        assert sum(c.max for c in developer.categories) <= developer.max_items

    def test_broken_profiles_fail(self, tmp_path: Path) -> None:
        source = profiles_module.PROFILES_DIR / "developer"
        for name in ("profile.json", "match.md", "score.md", "why.md"):
            (tmp_path / name).write_text((source / name).read_text())
        spec = json.loads((tmp_path / "profile.json").read_text())
        spec["id"] = tmp_path.name
        spec["categories"][0]["max"] = 99
        (tmp_path / "profile.json").write_text(json.dumps(spec))
        with pytest.raises(ProfileError, match="exceed max_items"):
            load_profile(tmp_path)
        spec["categories"][0]["max"] = 8
        spec["extra_sources"] = ["no-such-source"]
        (tmp_path / "profile.json").write_text(json.dumps(spec))
        with pytest.raises(ProfileError, match="unknown source"):
            load_profile(tmp_path)
        spec["extra_sources"] = []
        spec["template"] = "no-such-starter"
        (tmp_path / "profile.json").write_text(json.dumps(spec))
        with pytest.raises(ProfileError, match="unknown Starter"):
            load_profile(tmp_path)


class TestQuestions:
    def test_score_questions_come_from_the_files(self) -> None:
        developer = load_profiles()["developer"]
        score, category = score_questions(developer)
        assert score.kind == "score"
        assert score.options == tuple(str(i) for i in range(11))
        assert score.criteria["7"].startswith("a security issue")
        assert category.options == developer.category_ids
        assert category.criteria["security"]

    def test_route_and_resolve(self) -> None:
        loaded = load_profiles()
        route = route_question(list(loaded.values()))
        assert route.options[-1] == "none"
        assert set(route.criteria) == set(route.options)
        same = resolve_questions(3)
        assert [q.id for q in same] == ["same_0", "same_1", "same_2"]
        assert all(q.kind == "bool" for q in same)


class TestRouter:
    def test_sources_route_and_orphans_ask(self) -> None:
        loaded = load_profiles()
        assert "developer" in by_sources({"hackernews"}, loaded)
        assert by_sources({"no-such-source"}, loaded) == []
        assert needs_route_question({"no-such-source"}, 3, loaded)
        assert not needs_route_question({"no-such-source"}, 1, loaded)
        assert not needs_route_question({"hackernews"}, 5, loaded)
