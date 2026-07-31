"""Minimal HTTP client for the Carvera community firmware status API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

REQUEST_TIMEOUT_S = 4.0


class CarveraApiError(Exception):
    """Raised when the machine cannot be reached or answers garbage."""


class CarveraApiClient:
    """Client for GET http://<machine>:<port>/status."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self.host = host
        self.port = port

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch and parse the machine status document."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_S):
                resp = await self._session.get(f"{self.base_url}/status")
                resp.raise_for_status()
                # firmware sends Content-Type: application/json; be lenient anyway
                data = await resp.json(content_type=None)
        except TimeoutError as err:
            raise CarveraApiError(f"timeout talking to {self.base_url}") from err
        except aiohttp.ClientError as err:
            raise CarveraApiError(f"error talking to {self.base_url}: {err}") from err
        if not isinstance(data, dict) or "state" not in data:
            raise CarveraApiError(f"unexpected payload from {self.base_url}")
        return data
