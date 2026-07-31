"""Data update coordinator for the Carvera status API."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CarveraApiClient, CarveraApiError
from .beacon import BeaconListener
from .const import CONF_MACHINE_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CarveraCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /status, gated by the discovery beacon when available.

    Machines spend most of their life powered off. When the beacon
    listener is working, we skip HTTP entirely while no fresh beacon has
    been heard, so an off machine costs nothing and produces no timeouts.
    The beacon also tells us the machine's current IP, so a DHCP change
    while the machine was off heals automatically.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: CarveraApiClient,
        beacon: BeaconListener | None,
    ) -> None:
        self.client = client
        self.beacon = beacon
        self.machine_name: str = entry.data[CONF_MACHINE_NAME]
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{self.machine_name}",
            update_interval=timedelta(
                seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            ),
        )

    @property
    def machine_online(self) -> bool:
        """Best-effort online state, independent of entity availability."""
        if self.beacon is not None:
            info = self.beacon.get(self.machine_name)
            if info is not None and info.fresh:
                return True
        return self.last_update_success

    async def _async_update_data(self) -> dict[str, Any]:
        if self.beacon is not None and self.beacon.saw_any_beacon:
            info = self.beacon.get(self.machine_name)
            if info is None or not info.fresh:
                # Beacons are flowing on this network but not from this
                # machine: it is powered off. Fail fast, skip HTTP.
                raise UpdateFailed("machine is not announcing itself (powered off?)")
            if info.ip != self.client.host:
                _LOGGER.info(
                    "%s moved from %s to %s, following it",
                    self.machine_name,
                    self.client.host,
                    info.ip,
                )
                self.client.host = info.ip
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        CONF_HOST: info.ip,
                        CONF_PORT: self.client.port,
                    },
                )
        try:
            return await self.client.async_get_status()
        except CarveraApiError as err:
            raise UpdateFailed(str(err)) from err
