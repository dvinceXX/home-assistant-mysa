"""Read-only access to the Mysa cloud API."""

from __future__ import annotations

from collections.abc import Callable

import aiohttp
from mysa_client.cloud import MysaAuth, MysaClient

USER_AGENT = "HomeAssistant-Mysa/0.2.0"


def create_client(
    session: aiohttp.ClientSession,
    *,
    refresh_token: str | None = None,
    on_refresh_token: Callable[[str], None] | None = None,
    email: str | None = None,
    password: str | None = None,
) -> MysaClient:
    """Create an authenticated Mysa client for read-only operations."""
    auth = MysaAuth(
        session,
        refresh_token,
        user_agent=USER_AGENT,
        on_refresh_token=on_refresh_token,
        email=email,
        password=password,
    )
    return MysaClient(session, auth, user_agent=USER_AGENT)


async def async_validate_credentials(
    session: aiohttp.ClientSession, email: str, password: str
) -> tuple[MysaClient, str]:
    """Sign in and verify account access; return client and refresh token."""
    auth = MysaAuth(
        session,
        user_agent=USER_AGENT,
        email=email,
        password=password,
    )
    await auth.async_get_id_token()
    client = MysaClient(session, auth, user_agent=USER_AGENT)
    await client.bootstrap()
    if not auth.refresh_token:
        raise RuntimeError("Mysa authentication returned no refresh token")
    return client, auth.refresh_token
