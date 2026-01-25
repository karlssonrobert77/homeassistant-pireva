"""Config flow for Pireva Garbage Collection"""

import voluptuous as vol
from homeassistant import config_entries

from .const import CONF_ADDRESS


class PirevaConfigFlow(config_entries.ConfigFlow, domain="pireva"):
    """Handle a config flow for Pireva."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].lower().replace(" ", "")
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=address,
                data={CONF_ADDRESS: address},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): str,
            }),
        )
