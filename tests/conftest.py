"""Shared fixtures."""

from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading this custom integration in tests."""
    yield


@pytest.fixture(autouse=True)
def no_beacon_listener():
    """Never bind real UDP sockets in tests: beacon degrades to polling."""
    with patch(
        "custom_components.carvera.beacon.BeaconListener.async_start",
        return_value=False,
    ):
        yield
