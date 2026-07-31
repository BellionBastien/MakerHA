"""Binary sensors for the Carvera status API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CarveraConfigEntry
from .coordinator import CarveraCoordinator
from .entity import CarveraEntity


@dataclass(frozen=True, kw_only=True)
class CarveraBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[CarveraBinarySensorDescription, ...] = (
    CarveraBinarySensorDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("state") in ("Run", "Home"),
    ),
    CarveraBinarySensorDescription(
        key="alarm",
        translation_key="alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.get("alarm"),
    ),
    CarveraBinarySensorDescription(
        key="job_playing",
        translation_key="job_playing",
        icon="mdi:play-circle-outline",
        value_fn=lambda d: (d.get("job") or {}).get("playing"),
    ),
    CarveraBinarySensorDescription(
        key="controller_connected",
        translation_key="controller_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("controller_connected"),
    ),
    CarveraBinarySensorDescription(
        key="laser_mode",
        translation_key="laser_mode",
        icon="mdi:laser-pointer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.get("laser") or {}).get("mode"),
    ),
    CarveraBinarySensorDescription(
        key="vacuum_mode",
        translation_key="vacuum_mode",
        icon="mdi:fan-auto",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.get("spindle") or {}).get("vacuum"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarveraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BinarySensorEntity] = [
        CarveraBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    ]
    entities.append(CarveraOnlineSensor(coordinator))
    async_add_entities(entities)


class CarveraBinarySensor(CarveraEntity, BinarySensorEntity):
    """A binary sensor backed by one field of the status document."""

    entity_description: CarveraBinarySensorDescription

    def __init__(
        self,
        coordinator: CarveraCoordinator,
        description: CarveraBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data or {})


class CarveraOnlineSensor(CarveraEntity, BinarySensorEntity):
    """Powered-on state: stays available while the machine is off.

    Every other entity goes unavailable when the machine is off (which is
    most of the time); this one keeps reporting on/off so automations can
    react to the machine being powered on or off.
    """

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, coordinator: CarveraCoordinator) -> None:
        super().__init__(coordinator, "online")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.machine_online
