"""Config flow for the Makera Carvera (MakerHA) integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarveraApiClient, CarveraApiError
from .beacon import BeaconListener
from .const import (
    CONF_MACHINE_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DISCOVERY_LISTEN_S,
    DOMAIN,
)

MANUAL = "manual"


async def _async_discover(hass: HomeAssistant) -> dict[str, Any]:
    """Listen briefly for machine beacons; reuse the running listener if any."""
    shared: BeaconListener | None = hass.data.get(DOMAIN, {}).get("beacon")
    if shared is not None:
        await asyncio.sleep(DISCOVERY_LISTEN_S)
        return shared.machines()
    temp = BeaconListener()
    if not await temp.async_start():
        return {}
    try:
        await asyncio.sleep(DISCOVERY_LISTEN_S)
        return temp.machines()
    finally:
        temp.stop()


class CarveraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow: discover via beacon, fall back to manual."""

    VERSION = 1

    def __init__(self) -> None:
        self._found: dict[str, Any] = {}

    async def _async_validate(
        self, host: str, port: int
    ) -> tuple[dict[str, str], dict[str, Any] | None]:
        """Try the status endpoint; return (errors, status)."""
        client = CarveraApiClient(async_get_clientsession(self.hass), host, port)
        try:
            status = await client.async_get_status()
        except CarveraApiError:
            return {"base": "cannot_connect"}, None
        return {}, status

    async def _async_create(self, host: str, port: int) -> ConfigFlowResult:
        errors, status = await self._async_validate(host, port)
        if errors:
            return await self.async_step_manual(errors=errors, host=host, port=port)
        name = status["name"]
        await self.async_set_unique_id(name)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})
        return self.async_create_entry(
            title=name,
            data={CONF_HOST: host, CONF_PORT: port, CONF_MACHINE_NAME: name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: listen for beacons and offer what was found."""
        if user_input is not None:
            if user_input["machine"] == MANUAL:
                return await self.async_step_manual()
            info = self._found[user_input["machine"]]
            # The beacon carries the console port, not the HTTP port; the
            # status API listens on its own (default 8080) port.
            return await self._async_create(info.ip, DEFAULT_PORT)

        self._found = await _async_discover(self.hass)
        if not self._found:
            return await self.async_step_manual()

        options = {name: f"{name} ({info.ip})" for name, info in self._found.items()}
        options[MANUAL] = "Enter address manually"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("machine"): vol.In(options)}),
        )

    async def async_step_manual(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
        host: str = "",
        port: int = DEFAULT_PORT,
    ) -> ConfigFlowResult:
        """Manual entry of host and port."""
        if user_input is not None and errors is None:
            return await self._async_create(
                user_input[CONF_HOST].strip(), user_input[CONF_PORT]
            )
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=host): str,
                    vol.Required(CONF_PORT, default=port): int,
                }
            ),
            errors=errors or {},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> CarveraOptionsFlow:
        return CarveraOptionsFlow()


class CarveraOptionsFlow(OptionsFlow):
    """Options: polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "scan_interval",
                        default=self.config_entry.options.get(
                            "scan_interval", DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(int, vol.Range(min=2, max=60)),
                }
            ),
        )
