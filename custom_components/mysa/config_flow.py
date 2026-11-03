"""Config flow for Mysa."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class MysaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mysa."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial user step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].casefold())
            self._abort_if_unique_id_configured()
            # Authentication validation will be added with the read-only API client.
            return self.async_create_entry(
                title=user_input[CONF_EMAIL],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
