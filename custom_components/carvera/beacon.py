"""Listener for the Carvera UDP discovery beacon.

The firmware broadcasts ``NAME,IP,PORT,BUSY`` on UDP port 3333 once per
second while powered on. Listening to it gives us three things for free:

- discovery during the config flow (no IP typing),
- instant power-on/off detection for machines that sit turned off most
  of the time (no need to poll a dead host),
- automatic re-resolution of the machine's IP after a DHCP change.

The listener is optional: if the port cannot be bound or broadcasts do
not reach Home Assistant (container without host networking), the
integration falls back to plain HTTP polling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from .const import BEACON_PORT, BEACON_STALE_S

_LOGGER = logging.getLogger(__name__)


@dataclass
class BeaconInfo:
    """Last known beacon data for one machine."""

    name: str
    ip: str
    port: int
    busy: bool
    last_seen: float  # time.monotonic()

    @property
    def fresh(self) -> bool:
        return (time.monotonic() - self.last_seen) < BEACON_STALE_S


class BeaconListener(asyncio.DatagramProtocol):
    """Shared UDP listener; one instance serves every config entry."""

    def __init__(self) -> None:
        self._transport: asyncio.DatagramTransport | None = None
        self._machines: dict[str, BeaconInfo] = {}
        self._callbacks: list[Callable[[BeaconInfo], None]] = []
        self.saw_any_beacon = False

    async def async_start(self) -> bool:
        """Bind the UDP socket. Returns False when unavailable."""
        if self._transport is not None:
            return True
        loop = asyncio.get_running_loop()
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: self, local_addr=("0.0.0.0", BEACON_PORT)
            )
        except OSError as err:
            _LOGGER.warning(
                "Cannot listen for Carvera beacons on UDP %d (%s); "
                "falling back to plain polling",
                BEACON_PORT,
                err,
            )
            return False
        return True

    def stop(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    # -- DatagramProtocol -------------------------------------------------
    def connection_lost(self, exc: Exception | None) -> None:
        self._transport = None

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            parts = data.decode("ascii", errors="replace").strip().split(",")
            if len(parts) != 4:
                return
            info = BeaconInfo(
                name=parts[0],
                ip=parts[1],
                port=int(parts[2]),
                busy=parts[3] == "1",
                last_seen=time.monotonic(),
            )
        except (ValueError, IndexError):
            return
        self.saw_any_beacon = True
        self._machines[info.name] = info
        for callback in list(self._callbacks):
            callback(info)

    # -- accessors ---------------------------------------------------------
    def get(self, name: str) -> BeaconInfo | None:
        return self._machines.get(name)

    def machines(self) -> dict[str, BeaconInfo]:
        return dict(self._machines)

    def add_callback(self, callback: Callable[[BeaconInfo], None]) -> Callable[[], None]:
        self._callbacks.append(callback)

        def _remove() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return _remove
