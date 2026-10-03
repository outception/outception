import pytest
from httpx import AsyncClient

from outception.kit.versioning import APIVersion
from outception.version import VERSIONS


@pytest.mark.asyncio
@pytest.mark.parametrize("version", VERSIONS)
async def test_openapi(version: APIVersion, client: AsyncClient) -> None:
    response = await client.get(f"{version}/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "Scope" in schema["components"]["schemas"]
    assert schema["info"]["version"] == str(version)
    # The frozen-contract diff against a snapshot returns with the news routes:
    # the snapshot is taken once the public surface exists.
