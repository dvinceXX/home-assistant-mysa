"""Config flow for Mysa."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from mysa_client.cloud import (
    MysaAuthError,
    MysaConnectionError,
    MysaInvalidCredentialsError,
    MysaRateLimitError,
    MysaUnsupportedChallengeError,
)

from .api import async_validate_credentials
from .const import CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MysaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mysa."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Validate Mysa credentials and create the account entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].casefold())
            self._abort_if_unique_id_configured()

            try:
                _, refresh_token = await async_validate_credentials(
                    async_get_clientsession(self.hass),
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
            except MysaInvalidCredentialsError:
                errors["base"] = "invalid_auth"
            except MysaUnsupportedChallengeError:
                errors["base"] = "unsupported_auth"
            except MysaRateLimitError:
                errors["base"] = "rate_limited"
            except MysaConnectionError:
                errors["base"] = "cannot_connect"
            except MysaAuthError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to Mysa")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_REFRESH_TOKEN: refresh_token,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
