"""Serve and register the MakerHA dashboard card.

The card ships inside the integration, so installing MakerHA is enough for
"Carvera (MakerHA)" to appear in the dashboard card picker: the JS is served
from this folder and registered as a Lovelace resource automatically.

Registering a resource means touching `hass.data["lovelace"]`, which is not a
public API and has moved between releases - every access here is defensive and
a failure only costs the automatic registration (the card can still be added
by hand), never the integration setup.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = "/carvera_makerha"
CARD_FILENAME = "makerha-card.js"


def _lovelace(hass: HomeAssistant) -> Any | None:
    return hass.data.get("lovelace")


def _resource_mode(lovelace: Any) -> str | None:
    # 2026.2 renamed `mode` to `resource_mode`
    for attr in ("resource_mode", "mode"):
        mode = getattr(lovelace, attr, None)
        if mode is not None:
            return mode
    if isinstance(lovelace, dict):
        return lovelace.get("mode")
    return None


def _resources(lovelace: Any) -> Any | None:
    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    return resources


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and add it to the Lovelace resources (idempotent)."""
    if getattr(hass, "http", None) is None:
        _LOGGER.debug("No http component, skipping card registration")
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASE, str(pathlib.Path(__file__).parent), cache_headers=False)]
        )
    except RuntimeError:
        pass  # already registered by a previous entry
    except Exception as err:  # noqa: BLE001 - a card must never break setup
        _LOGGER.warning("Could not serve the MakerHA card (%s)", err)
        return

    try:
        integration = await async_get_integration(hass, DOMAIN)
        version = str(integration.version)
    except Exception:  # noqa: BLE001 - version is cosmetic cache-busting
        version = "0"
    url = f"{URL_BASE}/{CARD_FILENAME}?v={version}"

    lovelace = _lovelace(hass)
    if lovelace is None:
        _LOGGER.debug("Lovelace not set up yet, skipping card resource registration")
        return

    if _resource_mode(lovelace) != "storage":
        _LOGGER.info(
            "Dashboards are in YAML mode: add the MakerHA card manually with "
            "`resources: [{url: %s, type: module}]`",
            url,
        )
        return

    resources = _resources(lovelace)
    if resources is None:
        _LOGGER.debug("No Lovelace resource collection, skipping card registration")
        return

    try:
        if not getattr(resources, "loaded", True):
            await resources.async_load()
            resources.loaded = True

        for item in resources.async_items():
            if str(item.get("url", "")).startswith(f"{URL_BASE}/{CARD_FILENAME}"):
                if item["url"] != url:  # integration updated: refresh the cache buster
                    await resources.async_update_item(item["id"], {"url": url})
                return

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info("Registered the MakerHA dashboard card (%s)", url)
    except Exception as err:  # noqa: BLE001 - never break setup over a dashboard card
        _LOGGER.warning(
            "Could not register the MakerHA card automatically (%s). Add %s as a "
            "dashboard resource of type 'module' to use it",
            err,
            url,
        )


async def async_unregister_card(hass: HomeAssistant) -> None:
    """Remove the card resource, so an uninstall leaves no dangling entry."""
    lovelace = _lovelace(hass)
    if lovelace is None or _resource_mode(lovelace) != "storage":
        return
    resources = _resources(lovelace)
    if resources is None:
        return
    try:
        for item in list(resources.async_items()):
            if str(item.get("url", "")).startswith(f"{URL_BASE}/{CARD_FILENAME}"):
                await resources.async_delete_item(item["id"])
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not remove the MakerHA card resource: %s", err)
