"""Read-only access to the Mysa cloud API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import aiohttp
from mysa_client.cloud import MysaAuth, MysaClient

USER_AGENT = "HomeAssistant-Mysa/0.1.0"


def create_client(
    session: aiohttp.ClientSession,
    *,
    refresh_token: str | None = None,
    on_refresh_token: Callable[[str], None] | None = None,
) -> MysaClient:
    """Create an authenticated Mysa client without exposing control methods."""
    auth = MysaAuth(
        session,
        refresh_token,
        user_agent=USER_AGENT,
        on_refresh_token=on_refresh_token,
    )
    return MysaClient(session, auth, user_agent=USER_AGENT)


async def async_validate_credentials(
    session: aiohttp.ClientSession, email: str, password: str
) -> tuple[MysaClient, str]:
    """Sign in and verify account access; return client and refresh token."""
    auth = MysaAuth(session, user_agent=USER_AGENT)
    await auth.sign_in(email, password)
    client = MysaClient(session, auth, user_agent=USER_AGENT)
    await client.bootstrap()
    if not auth.refresh_token:
        raise RuntimeError("Mysa authentication returned no refresh token")
    return client, auth.refresh_token


async def async_get_device_states(client: MysaClient) -> dict[str, Any]:
    """Read current state for every device in the account."""
    account = await client.bootstrap()
    states: dict[str, Any] = {}
    for device_id in account.devices:
        states[device_id] = await client.get_state(device_id)
    return states
