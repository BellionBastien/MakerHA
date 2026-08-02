"""MakerHA - Home Assistant integration for Makera Carvera CNC machines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarveraApiClient
from .beacon import BeaconListener
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import CarveraCoordinator
from .frontend import async_register_card, async_unregister_card

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type CarveraConfigEntry = ConfigEntry[CarveraRuntimeData]


@dataclass
class CarveraRuntimeData:
    """Objects a config entry keeps alive."""

    coordinator: CarveraCoordinator


async def _async_get_shared_beacon(hass: HomeAssistant) -> BeaconListener | None:
    """One beacon listener shared by every config entry (refcounted)."""
    store = hass.data.setdefault(DOMAIN, {})
    if "beacon" not in store:
        listener = BeaconListener()
        store["beacon"] = listener if await listener.async_start() else None
    store["beacon_refs"] = store.get("beacon_refs", 0) + 1
    return store["beacon"]


def _release_shared_beacon(hass: HomeAssistant) -> None:
    store = hass.data.get(DOMAIN, {})
    store["beacon_refs"] = max(0, store.get("beacon_refs", 1) - 1)
    if store["beacon_refs"] == 0 and store.get("beacon") is not None:
        store["beacon"].stop()
        store.pop("beacon", None)


async def async_setup_entry(hass: HomeAssistant, entry: CarveraConfigEntry) -> bool:
    """Set up a Carvera from a config entry."""
    await async_register_card(hass)
    beacon = await _async_get_shared_beacon(hass)
    client = CarveraApiClient(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT]
    )
    coordinator = CarveraCoordinator(hass, entry, client, beacon)

    # Machines are usually powered off: do not fail setup when the first
    # refresh fails, entities simply start unavailable and recover on the
    # next beacon/poll.
    await coordinator.async_refresh()

    entry.runtime_data = CarveraRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: CarveraConfigEntry) -> None:
    """Apply option changes in place.

    No reload here: the coordinator itself updates the entry data when a
    machine comes back with a new DHCP lease, and reloading from inside
    that update would tear the coordinator down mid-poll.
    """
    entry.runtime_data.coordinator.update_interval = timedelta(
        seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    )


async def async_unload_entry(hass: HomeAssistant, entry: CarveraConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _release_shared_beacon(hass)
        # last machine gone: take the card resource with it
        if len(hass.config_entries.async_loaded_entries(DOMAIN)) <= 1:
            await async_unregister_card(hass)
    return unload_ok
