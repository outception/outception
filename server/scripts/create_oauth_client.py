"""Create the OAuth2 client the mobile app signs in through.

A public client (PKCE, no secret) with the app's redirect, the user scopes
and an optional fixed client id so a rebuilt database keeps the id the
shipped app was built with.

    uv run python -m scripts.create_oauth_client --name "Outception app" \\
        --redirect outception://oauth/callback [--client-id outception_ci_...]
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from outception.kit.db.postgres import create_async_sessionmaker
from outception.models import OAuth2Client
from outception.oauth2.constants import CLIENT_ID_PREFIX
from outception.postgres import create_async_engine

DEFAULT_SCOPES = "openid profile email user:read user:write"


async def create(name: str, redirect: str, client_id: str | None, scopes: str) -> str:
    engine = create_async_engine("script")
    sessionmaker = create_async_sessionmaker(engine)
    async with sessionmaker() as session:
        if client_id is not None:
            existing = await session.scalar(
                select(OAuth2Client).where(OAuth2Client.client_id == client_id)
            )
            if existing is not None:
                print(f"client {client_id} already exists")
                return client_id
        client = OAuth2Client(
            client_id=client_id or f"{CLIENT_ID_PREFIX}{name.lower().replace(' ', '-')}"
        )
        client.set_client_metadata(
            {
                "client_name": name,
                "redirect_uris": [redirect],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": scopes,
                "default_sub_type": "user",
            }
        )
        session.add(client)
        await session.commit()
        created = client.client_id
    await engine.dispose()
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="Outception app")
    parser.add_argument("--redirect", default="outception://oauth/callback")
    parser.add_argument(
        "--client-id",
        default=None,
        help="a fixed client id, for parity with the shipped app",
    )
    parser.add_argument("--scopes", default=DEFAULT_SCOPES)
    args = parser.parse_args(argv)
    client_id = asyncio.run(
        create(args.name, args.redirect, args.client_id, args.scopes)
    )
    print(f"client_id={client_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
