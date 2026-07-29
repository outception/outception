import json

import pytest
from pytest_mock import MockerFixture

from outception.exceptions import OutceptionError
from outception.news import games
from outception.news.fetch import NewsFetchError
from outception.redis import Redis

# The syndicate text format is strictly line-positional (see games.py):
# 2 = id, 4 = title, 6 = author, 8 = rows, 10 = cols, 12/14 = clue counts,
# grid from 16, across clues from 17+rows, down clues from 18+rows+across.
#
# 3x3 puzzle:   A B #
#               C D E
#               # F G
_TEXT = "\n".join(
    [
        "ARCHIVE",  # 0
        "",
        "260819",  # 2: id
        "",
        "Test Title",  # 4
        "",
        "Test Author",  # 6
        "",
        "3",  # 8: rows
        "",
        "3",  # 10: cols
        "",
        "3",  # 12: across count
        "",
        "3",  # 14: down count
        "",
        "AB#",  # 16: grid
        "CDE",
        "#FG",
        "",
        "Across one",  # 20: across clues (17 + rows)
        "Across three",
        "Across five",
        "",
        "Down one",  # 24: down clues (18 + rows + across)
        "Down two",
        "Down four",
    ]
)


class TestParseCrossword:
    def test_grid_and_meta(self) -> None:
        puzzle = games.parse_crossword(_TEXT)
        assert puzzle["id"] == "260819"
        assert puzzle["title"] == "Test Title"
        assert puzzle["author"] == "Test Author"
        assert puzzle["rows"] == 3
        assert puzzle["cols"] == 3
        assert puzzle["grid"] == ["AB#", "CDE", "#FG"]

    def test_standard_numbering(self) -> None:
        puzzle = games.parse_crossword(_TEXT)
        assert [(c["num"], c["row"], c["col"], c["len"]) for c in puzzle["across"]] == [
            (1, 0, 0, 2),
            (3, 1, 0, 3),
            (5, 2, 1, 2),
        ]
        assert [(c["num"], c["row"], c["col"], c["len"]) for c in puzzle["down"]] == [
            (1, 0, 0, 2),
            (2, 0, 1, 3),
            (4, 1, 2, 2),
        ]
        assert [c["clue"] for c in puzzle["across"]] == [
            "Across one",
            "Across three",
            "Across five",
        ]
        assert [c["clue"] for c in puzzle["down"]] == [
            "Down one",
            "Down two",
            "Down four",
        ]

    def test_void_padding_trimmed(self) -> None:
        # Larger deliveries pad the grid with '.' rows — trimmed before
        # numbering so counts match the declared clue lists.
        padded = _TEXT.replace("3\n\n3\n\n3\n\n3", "4\n\n3\n\n3\n\n3", 1)
        padded = padded.replace("AB#\nCDE\n#FG", "AB#\nCDE\n#FG\n...")
        puzzle = games.parse_crossword(padded)
        assert puzzle["rows"] == 3
        assert puzzle["grid"] == ["AB#", "CDE", "#FG"]
        assert len(puzzle["across"]) == 3
        assert len(puzzle["down"]) == 3

    def test_one_cell_runs_are_not_words(self) -> None:
        # A cell walled in on one axis belongs only to the crossing word —
        # it never gets its own clue (standard numbering).
        text = "\n".join([
            "ARCHIVE", "", "260820", "", "T", "", "A", "",
            "3", "", "3", "", "1", "", "3", "",
            "A#B", "CDE", "#F#", "",
            "Across three", "",
            "Down one", "Down two", "Down four",
        ])
        puzzle = games.parse_crossword(text)
        assert [(c["num"], c["len"]) for c in puzzle["across"]] == [(3, 3)]
        assert [(c["num"], c["len"]) for c in puzzle["down"]] == [
            (1, 2), (2, 2), (4, 2),
        ]

    def test_garbage_raises(self) -> None:
        with pytest.raises((ValueError, IndexError)):
            games.parse_crossword("not a puzzle")


@pytest.mark.asyncio
class TestGetCrossword:
    async def test_cache_hit_skips_upstream(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        fetch_mock = mocker.patch("outception.news.games.fetch_text")
        await redis.set(
            "news:games:crossword:260819", json.dumps({"id": "cached"})
        )

        puzzle = await games.get_crossword(redis, "260819")

        assert puzzle == {"id": "cached"}
        fetch_mock.assert_not_called()

    async def test_fetch_success_caches(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch("outception.news.games.fetch_text", return_value=_TEXT)

        puzzle = await games.get_crossword(redis, "260819")

        assert puzzle["id"] == "260819"
        cached = await redis.get("news:games:crossword:260819")
        assert cached is not None
        assert json.loads(cached)["id"] == "260819"

    async def test_fetch_failure_sets_marker(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        fetch_mock = mocker.patch(
            "outception.news.games.fetch_text",
            side_effect=NewsFetchError("HTTP 404"),
        )

        with pytest.raises(OutceptionError) as exc_info:
            await games.get_crossword(redis, "260819")
        assert exc_info.value.status_code == 502
        assert await redis.get("news:games:crossword:fail:260819") is not None

        # The marker short-circuits: no second upstream hit while it lives.
        with pytest.raises(OutceptionError):
            await games.get_crossword(redis, "260819")
        assert fetch_mock.call_count == 1

    async def test_falls_back_to_yesterday(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.games.fetch_text",
            side_effect=NewsFetchError("HTTP 404"),
        )
        await redis.set(
            "news:games:crossword:260818", json.dumps({"id": "yesterday"})
        )

        puzzle = await games.get_crossword(redis, "260819", "260818")

        assert puzzle == {"id": "yesterday"}

    async def test_no_fallback_available_raises(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.games.fetch_text",
            side_effect=NewsFetchError("HTTP 404"),
        )

        with pytest.raises(OutceptionError) as exc_info:
            await games.get_crossword(redis, "260819", "260818")
        assert exc_info.value.status_code == 502
