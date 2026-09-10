import pytest
from httpx import AsyncClient

from outception.news.metadata import SOURCES
from outception.news.registry import DISABLED_SOURCES
from outception.news.templates import _TEMPLATES, resolve_templates


@pytest.mark.asyncio
class TestTemplatesEndpoint:
    async def test_returns_persona_bundles(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/news/templates")).json()
        ids = [t["id"] for t in body["templates"]]
        assert "developer" in ids
        assert "news-junkie" in ids
        # No country known → no localized my-country bundle.
        assert "my-country" not in ids
        dev = next(t for t in body["templates"] if t["id"] == "developer")
        assert "github" in dev["sources"]
        assert "hackernews" in dev["sources"]

    async def test_country_localises_bundles(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/news/templates", params={"country": "IE"})).json()
        by_id = {t["id"]: t["sources"] for t in body["templates"]}
        # Sports fan gets the visitor country's sports, not just generics.
        assert "sport-gaelic-football" in by_id["sports-fan"]
        # My-country resolves fully from the IP country.
        assert "gnews-ie" in by_id["my-country"]
        assert "property-ie" in by_id["my-country"]

    async def test_every_resolved_source_is_real(self) -> None:
        for cc in (None, "IE", "US", "DE", "ZZ"):
            for template in resolve_templates(cc):
                for sid in template["sources"]:
                    assert sid in SOURCES, (cc, template["id"], sid)
                    assert sid not in DISABLED_SOURCES, (cc, template["id"], sid)

    def test_static_ids_exist_or_are_key_gated(self) -> None:
        # Static bundle entries must be roster ids (heatmaps may be key-gated
        # away in this env - they're validated live in resolve_templates).
        from outception.news.heatmap import HEATMAPS

        for template in _TEMPLATES:
            for sid in template.sources:
                assert sid in SOURCES or sid in HEATMAPS, (template.id, sid)
