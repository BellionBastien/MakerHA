"""Constants for the Makera Carvera (MakerHA) integration."""

from __future__ import annotations

DOMAIN = "carvera"

DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 5  # seconds
BEACON_PORT = 3333
BEACON_STALE_S = 15.0  # beacon older than this -> machine considered off
DISCOVERY_LISTEN_S = 3.0

CONF_MACHINE_NAME = "machine_name"

# Machine states as reported by the firmware (Kernel::get_query_string)
MACHINE_STATES = [
    "Idle",
    "Run",
    "Home",
    "Hold",
    "Alarm",
    "Sleep",
    "Pause",
    "Wait",
    "Tool",
]

MODEL_NAMES = {
    "C1": "Carvera",
    "CA1": "Carvera Air",
}
