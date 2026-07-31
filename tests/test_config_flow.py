"""Config flow tests."""

import time
from unittest.mock import patch

import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.carvera.beacon import BeaconInfo
from custom_components.carvera.const import DOMAIN

from .const import ENTRY_DATA, SAMPLE_STATUS

NO_DISCOVERY = patch(
    "custom_components.carvera.config_flow._async_discover", return_value={}
)


async def test_manual_flow_success(hass: HomeAssistant, aioclient_mock) -> None:
    """No machine discovered -> manual entry -> entry created."""
    with NO_DISCOVERY:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    aioclient_mock.get("http://1.2.3.4:8080/status", json=SAMPLE_STATUS)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "1.2.3.4", "port": 8080}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CARVERA_AIR_05214"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == "CARVERA_AIR_05214"


async def test_manual_flow_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    """Unreachable machine -> error on the manual form."""
    with NO_DISCOVERY:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    aioclient_mock.get("http://1.2.3.4:8080/status", exc=aiohttp.ClientError("boom"))
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "1.2.3.4", "port": 8080}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_discovery_pick(hass: HomeAssistant, aioclient_mock) -> None:
    """Machine found by beacon -> pick it -> entry created with its IP."""
    info = BeaconInfo(
        name="CARVERA_AIR_05214",
        ip="5.6.7.8",
        port=2222,
        busy=False,
        last_seen=time.monotonic(),
    )
    with patch(
        "custom_components.carvera.config_flow._async_discover",
        return_value={info.name: info},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    aioclient_mock.get("http://5.6.7.8:8080/status", json=SAMPLE_STATUS)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"machine": "CARVERA_AIR_05214"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "5.6.7.8"
    assert result["data"]["machine_name"] == "CARVERA_AIR_05214"


async def test_already_configured(hass: HomeAssistant, aioclient_mock) -> None:
    """Adding the same machine twice aborts."""
    MockConfigEntry(
        domain=DOMAIN, unique_id="CARVERA_AIR_05214", data=ENTRY_DATA
    ).add_to_hass(hass)

    with NO_DISCOVERY:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    aioclient_mock.get("http://1.2.3.4:8080/status", json=SAMPLE_STATUS)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "1.2.3.4", "port": 8080}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
