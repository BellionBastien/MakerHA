"""Entry setup / teardown tests."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.carvera.const import DOMAIN

from .const import ENTRY_DATA, SAMPLE_STATUS


async def test_setup_creates_entities(hass: HomeAssistant, aioclient_mock) -> None:
    """A configured machine sets up and exposes its entities."""
    aioclient_mock.get("http://1.2.3.4:8080/status", json=SAMPLE_STATUS)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="CARVERA_AIR_05214", data=ENTRY_DATA
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get("sensor.carvera_air_05214_state")
    assert state is not None
    assert state.state == "Idle"
    assert state.attributes["wcs"] == "G54"

    temp = hass.states.get("sensor.carvera_air_05214_spindle_temperature")
    assert temp is not None
    assert float(temp.state) == 29.3

    online = hass.states.get("binary_sensor.carvera_air_05214_online")
    assert online is not None
    assert online.state == "on"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_survives_without_frontend(hass: HomeAssistant, aioclient_mock) -> None:
    """Registering the dashboard card must never be able to fail setup.

    The test harness has no http component, which is exactly the shape of
    "the frontend is not available" this guards against.
    """
    aioclient_mock.get("http://1.2.3.4:8080/status", json=SAMPLE_STATUS)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="CARVERA_AIR_05214", data=ENTRY_DATA
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_setup_survives_machine_off(hass: HomeAssistant, aioclient_mock) -> None:
    """Setting up while the machine is off must not fail the entry."""
    aioclient_mock.get("http://1.2.3.4:8080/status", exc=TimeoutError())
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="CARVERA_AIR_05214", data=ENTRY_DATA
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get("sensor.carvera_air_05214_state")
    assert state is not None
    assert state.state == "unavailable"

    online = hass.states.get("binary_sensor.carvera_air_05214_online")
    assert online is not None
    assert online.state == "off"
