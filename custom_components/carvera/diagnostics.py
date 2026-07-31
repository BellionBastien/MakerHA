"""Diagnostics support for the Carvera integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import CarveraConfigEntry

TO_REDACT = {CONF_HOST, "ip"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CarveraConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    beacon_info = None
    if coordinator.beacon is not None:
        info = coordinator.beacon.get(coordinator.machine_name)
        if info is not None:
            beacon_info = {
                "fresh": info.fresh,
                "busy": info.busy,
                "console_port": info.port,
            }
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "beacon_listener_active": coordinator.beacon is not None,
        "beacon": beacon_info,
        "status": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
