"""Shared entity base for the Carvera integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODEL_NAMES
from .coordinator import CarveraCoordinator


class CarveraEntity(CoordinatorEntity[CarveraCoordinator]):
    """Base entity: device grouping + naming."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CarveraCoordinator, key: str) -> None:
        super().__init__(coordinator)
        name = coordinator.machine_name
        data = coordinator.data or {}
        self._attr_unique_id = f"{name}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, name)},
            name=name,
            manufacturer="Makera",
            model=MODEL_NAMES.get(data.get("model", ""), data.get("model")),
            sw_version=data.get("fw"),
            configuration_url=coordinator.client.base_url,
        )
