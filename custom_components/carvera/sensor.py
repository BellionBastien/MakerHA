"""Sensors for the Carvera status API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CarveraConfigEntry
from .const import MACHINE_STATES
from .coordinator import CarveraCoordinator
from .entity import CarveraEntity


def _g(data: dict[str, Any], *path: str) -> Any:
    """Nested dict get, None-safe."""
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data


def _tool(value: Any) -> Any:
    """Tool numbers below zero mean 'no tool'."""
    return None if value is None or value < 0 else value


def _length_unit(data: dict[str, Any]) -> str:
    """The firmware reports converted values while in inch mode (G20)."""
    return "in" if data.get("inch") else "mm"


def _feed_unit(data: dict[str, Any]) -> str:
    return "in/min" if data.get("inch") else "mm/min"


@dataclass(frozen=True, kw_only=True)
class CarveraSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[dict[str, Any]], Any]
    exists_fn: Callable[[dict[str, Any]], bool] = lambda data: True
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    # dynamic unit (inch vs metric mode); when set it wins over
    # native_unit_of_measurement
    unit_fn: Callable[[dict[str, Any]], str] | None = None


SENSORS: tuple[CarveraSensorDescription, ...] = (
    CarveraSensorDescription(
        key="state",
        translation_key="state",
        device_class=SensorDeviceClass.ENUM,
        options=MACHINE_STATES,
        value_fn=lambda d: d.get("state"),
        attributes_fn=lambda d: {
            "machine_position": d.get("mpos"),
            "work_position": d.get("wpos"),
            "wcs": d.get("wcs"),
            "wcs_rotation": d.get("wcs_rotation"),
            "inch_mode": d.get("inch"),
            "absolute_mode": d.get("absolute"),
        },
    ),
    CarveraSensorDescription(
        key="spindle_speed",
        translation_key="spindle_speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:rotate-right",
        value_fn=lambda d: _g(d, "spindle", "rpm"),
    ),
    CarveraSensorDescription(
        key="spindle_temperature",
        translation_key="spindle_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _g(d, "spindle", "temp"),
        exists_fn=lambda d: _g(d, "spindle", "temp") is not None,
    ),
    CarveraSensorDescription(
        key="power_temperature",
        translation_key="power_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("power_temp"),
        exists_fn=lambda d: "power_temp" in d,
    ),
    CarveraSensorDescription(
        key="feed_rate",
        translation_key="feed_rate",
        # no state_class: the unit follows the machine's G20/G21 mode and
        # long-term statistics cannot mix mm/min with in/min
        icon="mdi:speedometer",
        value_fn=lambda d: _g(d, "feed", "current"),
        unit_fn=_feed_unit,
    ),
    CarveraSensorDescription(
        key="feed_override",
        translation_key="feed_override",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune",
        value_fn=lambda d: _g(d, "feed", "override"),
    ),
    CarveraSensorDescription(
        key="spindle_override",
        translation_key="spindle_override",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        value_fn=lambda d: _g(d, "spindle", "override"),
    ),
    CarveraSensorDescription(
        key="tool",
        translation_key="tool",
        icon="mdi:tools",
        value_fn=lambda d: _tool(_g(d, "tool", "number")),
    ),
    CarveraSensorDescription(
        key="target_tool",
        translation_key="target_tool",
        icon="mdi:hammer-wrench",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _tool(_g(d, "tool", "target")),
    ),
    CarveraSensorDescription(
        key="tool_offset",
        translation_key="tool_offset",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:arrow-expand-vertical",
        value_fn=lambda d: _g(d, "tool", "offset"),
        unit_fn=_length_unit,
    ),
    CarveraSensorDescription(
        key="job_progress",
        translation_key="job_progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:progress-clock",
        value_fn=lambda d: _g(d, "job", "percent"),
    ),
    CarveraSensorDescription(
        key="job_file",
        translation_key="job_file",
        icon="mdi:file-cog",
        value_fn=lambda d: (_g(d, "job", "file") or "").split("/")[-1] or None,
    ),
    CarveraSensorDescription(
        key="job_elapsed",
        translation_key="job_elapsed",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:timer-outline",
        value_fn=lambda d: _g(d, "job", "elapsed_secs"),
    ),
    CarveraSensorDescription(
        key="probe_voltage",
        translation_key="probe_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("probe_voltage"),
        exists_fn=lambda d: "probe_voltage" in d,
    ),
    CarveraSensorDescription(
        key="laser_power",
        translation_key="laser_power",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:laser-pointer",
        value_fn=lambda d: _g(d, "laser", "power"),
        exists_fn=lambda d: "laser" in d,
    ),
    CarveraSensorDescription(
        key="halt_reason",
        translation_key="halt_reason",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.get("halt_reason"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarveraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors, skipping ones this machine never reports."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data or {}
    async_add_entities(
        CarveraSensor(coordinator, description)
        for description in SENSORS
        if not data or description.exists_fn(data)
    )


class CarveraSensor(CarveraEntity, SensorEntity):
    """A sensor backed by one field of the status document."""

    entity_description: CarveraSensorDescription

    def __init__(
        self, coordinator: CarveraCoordinator, description: CarveraSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn is not None:
            return self.entity_description.unit_fn(self.coordinator.data or {})
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data or {})
