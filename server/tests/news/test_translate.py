from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.config import settings
from outception.news import translate
from outception.news.fetch import NewsFetchError

# Google translate_a/single response shape for "Hello" -> German.
_GGL = [[["Hallo", "Hello", None, None, 10]], None, "en"]

# Batch response: newline-joined input comes back as one segment per line, with
# the separators preserved (the last segment has none).
_GGL_BATCH = [
    [["Hallo\n", "Hello\n"], ["Welt\n", "World\n"], ["Nachrichten", "News"]],
    None,
    "en",
]


class TestLangCodes:
    def test_google_code(self) -> None:
        assert translate._google_code("pt-PT") == "pt"
        assert translate._google_code("de") == "de"
        assert translate._google_code("zh-Hant") == "zh-TW"

    def test_libre_code_maps_to_argos_codes(self) -> None:
        assert translate._libre_code("pt-PT") == "pt"
        assert translate._libre_code("zh-Hans") == "zh"  # Argos uses zh / zt
        assert translate._libre_code("zh-Hant") == "zt"
        assert translate._libre_code("de") == "de"


class _LibreResponse:
    def __init__(self, translations: list[str]) -> None:
        self._translations = translations

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"translatedText": self._translations}


@pytest.mark.asyncio
class TestTranslateEndpoint:
    async def test_english_target_is_a_noop(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch.object(translate, "fetch_json", AsyncMock())
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "en"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hello"]
        fetch.assert_not_awaited()  # never calls the upstream for English

    async def test_translates_and_preserves_order(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(translate, "fetch_json", AsyncMock(return_value=_GGL))
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "de"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hallo"]

    async def test_batches_many_headlines_into_one_call(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch.object(
            translate, "fetch_json", AsyncMock(return_value=_GGL_BATCH)
        )
        response = await client.post(
            "/v1/news/translate",
            json={"texts": ["Hello", "World", "News"], "target": "de"},
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hallo", "Welt", "Nachrichten"]
        fetch.assert_awaited_once()  # one upstream request for the whole batch

    async def test_second_request_served_from_cache(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch.object(
            translate, "fetch_json", AsyncMock(return_value=_GGL)
        )
        body = {"texts": ["Hello"], "target": "de"}
        await client.post("/v1/news/translate", json=body)
        await client.post("/v1/news/translate", json=body)
        fetch.assert_awaited_once()  # cached on the second call

    async def test_upstream_failure_falls_back_to_original(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            translate,
            "fetch_json",
            AsyncMock(side_effect=NewsFetchError("boom")),
        )
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "de"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hello"]

    async def test_empty_texts_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/news/translate", json={"texts": [], "target": "de"}
        )
        assert response.status_code == 422

    async def test_public_success_skips_libretranslate(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # The fast public endpoint is primary; when it succeeds, the self-hosted
        # LibreTranslate fallback is never touched.
        mocker.patch.object(
            settings, "LIBRETRANSLATE_URL", "http://libretranslate:5000"
        )
        google = mocker.patch.object(
            translate, "fetch_json", AsyncMock(return_value=_GGL)
        )
        post = mocker.patch.object(translate._libre_client, "post", AsyncMock())
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "de"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hallo"]
        google.assert_awaited()  # public endpoint tried first
        post.assert_not_awaited()  # no fallback needed

    async def test_falls_back_to_libretranslate_when_public_fails(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # When the public endpoint can't translate (e.g. it's rate-limiting),
        # the miss is retried through LibreTranslate in the background.
        mocker.patch.object(
            settings, "LIBRETRANSLATE_URL", "http://libretranslate:5000"
        )
        google = mocker.patch.object(
            translate,
            "fetch_json",
            AsyncMock(side_effect=NewsFetchError("rate limited")),
        )
        post = mocker.patch.object(
            translate._libre_client,
            "post",
            AsyncMock(return_value=_LibreResponse(["Hallo"])),
        )
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "de"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hallo"]
        google.assert_awaited()  # public endpoint tried first
        post.assert_awaited_once()  # LibreTranslate filled the miss

    async def test_serbian_croatian_bypass_libretranslate(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # Even with LibreTranslate configured — and even when the public endpoint
        # fails — sr/hr (which LibreTranslate lacks a model for) never fall back
        # to it; they stay on the public endpoint and degrade to the original.
        mocker.patch.object(
            settings, "LIBRETRANSLATE_URL", "http://libretranslate:5000"
        )
        libre = mocker.patch.object(translate._libre_client, "post", AsyncMock())
        google = mocker.patch.object(
            translate,
            "fetch_json",
            AsyncMock(side_effect=NewsFetchError("rate limited")),
        )
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "sr"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == [
            "Hello"
        ]  # original, not LibreTranslate
        google.assert_awaited()  # public endpoint used
        libre.assert_not_awaited()  # LibreTranslate skipped for Serbian

    async def test_identical_translation_is_not_a_miss(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # A headline that translates to itself (a brand, or text already in the
        # target language) is a SUCCESS, not a miss — it must not be re-sent to
        # LibreTranslate and overwritten with a different rendering.
        mocker.patch.object(
            settings, "LIBRETRANSLATE_URL", "http://libretranslate:5000"
        )
        mocker.patch.object(
            translate,
            "fetch_json",
            AsyncMock(
                return_value=[[["Google", "Google", None, None, 10]], None, "en"]
            ),
        )
        post = mocker.patch.object(translate._libre_client, "post", AsyncMock())
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Google"], "target": "de"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Google"]
        post.assert_not_awaited()  # identical output is not treated as a failure

    async def test_failed_translation_is_not_cached(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # A genuine failure (Google down, no LibreTranslate) returns the original
        # but must NOT be cached, so a later request retries instead of serving
        # the untranslated headline for the full 24h TTL.
        fetch = mocker.patch.object(
            translate,
            "fetch_json",
            AsyncMock(side_effect=NewsFetchError("rate limited")),
        )
        body = {"texts": ["Hello"], "target": "de"}
        first = await client.post("/v1/news/translate", json=body)
        assert first.json()["translations"] == ["Hello"]  # degraded to original

        fetch.side_effect = None
        fetch.return_value = _GGL
        second = await client.post("/v1/news/translate", json=body)
        assert second.json()["translations"] == ["Hallo"]  # retried, not cached-stale
