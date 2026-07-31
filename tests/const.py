"""Shared test data: a status payload captured from a real Carvera Air."""

SAMPLE_STATUS = {
    "name": "CARVERA_AIR_05214",
    "model": "CA1",
    "fw": "http-status-api-75dd4b1",
    "ip": "1.2.3.4",
    "state": "Idle",
    "alarm": False,
    "halt_reason": 0,
    "mpos": [-2.0, -2.0, -2.0, 0.5, 0.0],
    "wpos": [274.185, 177.57, 94.6016, 0.5, 0.0],
    "wcs": "G54",
    "wcs_rotation": 0.0,
    "inch": False,
    "absolute": True,
    "feed": {"current": 0.0, "target": 3000.0, "override": 100.0},
    "spindle": {
        "on": False,
        "rpm": 0.0,
        "target_rpm": 10000.0,
        "override": 100.0,
        "pwm": 0.0,
        "vacuum": False,
        "temp": 29.3,
    },
    "power_temp": 29.9,
    "tool": {"number": 1, "target": -1, "offset": 20.385},
    "probe_voltage": 0.0,
    "laser": {"mode": False, "on": False, "power": 0.0, "scale": 100.0},
    "job": {"playing": False},
    "leveling": {"active": False},
    "clients": 0,
    "controller_connected": False,
}

ENTRY_DATA = {"host": "1.2.3.4", "port": 8080, "machine_name": "CARVERA_AIR_05214"}
