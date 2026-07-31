<p align="center"><img src="docs/icon.png" width="112" alt="Makera logo"></p>

# MakerHA — Makera Carvera for Home Assistant

*Makera yourself at home.*

> [!IMPORTANT]
> **Unofficial community project.** This integration is developed by the community and is **not affiliated with,
> endorsed by, or supported by Makera Inc.** in any way. *Makera* and *Carvera* are trademarks of Makera Inc.; the
> name and logo are used solely to identify the machines this integration works with. Don't contact Makera for
> support with this integration — open an issue here instead.

[![HACS Custom](https://img.shields.io/badge/HACS-custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/BellionBastien/MakerHA/actions/workflows/validate.yml/badge.svg)](https://github.com/BellionBastien/MakerHA/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![HA 2025.6+](https://img.shields.io/badge/Home%20Assistant-2025.6%2B-blue)

Local, no-cloud Home Assistant integration for [Makera Carvera](https://www.makera.com) CNC machines running the
[Community Firmware](https://github.com/Carvera-Community/Carvera_Community_Firmware) with the read-only HTTP status API.

Know when your machine is waiting for a tool change, get pinged when the job finishes or alarms, chart your spindle
temperature, and switch the dust extraction with the machine — all local, nothing leaves your network.

<!-- TODO: add docs/device-page.png (screenshot of the HA device page) — a picture sells this better than any text -->

> **Status: early (v0.1.x).** Running against a Carvera Air on the `http-status-api` firmware branch. Feedback and
> issue reports are very welcome — this is being shared to find out what other people need.

- **Auto-discovery** — machines are found via the Carvera's own UDP announcement; no IP typing, and the integration
  follows the machine across DHCP lease changes automatically.
- **Built for machines that are usually off** — entities go unavailable while the CNC is powered down (no error spam,
  no timeouts: polling is gated on the announcement beacon), and an always-available **Online** sensor lets you
  automate on power-on/power-off.
- **Ready-made device triggers** — *Tool change required*, *Job started*, *Job finished*, *Alarm raised* — so the
  headline automation ("ping my phone when the machine waits for a tool") is a two-click affair.
- **Read-only by design** — the firmware API is GET-only; nothing on your network can control the machine through it.

## Requirements

- A Carvera or Carvera Air running the Community Firmware **with the HTTP status API** (feature branch
  [`http-status-api`](https://github.com/Carvera-Community/Carvera_Community_Firmware), upstream PR pending), enabled once via the console:

  ```
  config-set sd wifi.http_enable true
  reset
  ```

- Home Assistant 2025.6 or newer.
- For discovery and off-detection, Home Assistant must be able to receive UDP broadcasts on port 3333 (true for Home
  Assistant OS and container installs with host networking). Without it, the integration still works by plain polling.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=BellionBastien&repository=MakerHA&category=integration)

1. Click the badge above (or: HACS → three-dot menu → **Custom repositories** → add
   `https://github.com/BellionBastien/MakerHA` as type *Integration*).
2. Download **MakerHA**, restart Home Assistant.
3. Settings → Devices & Services → **Add integration** → *Makera Carvera (MakerHA)*. Machines that are powered on
   appear in a pick list; select one and you're done.

### Manual

Copy `custom_components/carvera/` into your Home Assistant `config/custom_components/` directory and restart.

## Entities

| Entity | Type | Notes |
|---|---|---|
| State | sensor (enum) | `Idle · Run · Home · Hold · Alarm · Sleep · Pause · Wait · Tool` — positions (MPos/WPos), WCS and modes as attributes |
| Spindle speed | sensor | RPM |
| Spindle temperature | sensor | °C, long-term statistics |
| Power supply temperature | sensor | °C (Carvera Air) |
| Feed rate / Feed override / Spindle override | sensor | mm/min, % |
| Tool / Target tool / Tool offset | sensor | tool numbers; below-zero means "none" |
| Job progress / Job file / Job elapsed | sensor | %, filename, seconds |
| Wireless probe battery | sensor | V (diagnostic) |
| Laser power | sensor | % (diagnostic) |
| Halt reason | sensor | firmware halt code (diagnostic) |
| Running / Alarm / Job playing | binary sensor | |
| Controller connected | binary sensor | someone is on the console port |
| Laser mode / Vacuum mode | binary sensor | diagnostic |
| **Online** | binary sensor | stays available while the machine is off — automate on power-on |

## Example automations

**Tool change notification** (the reason this exists):

```yaml
automation:
  - alias: "Carvera: tool change needed"
    mode: single
    triggers:
      - trigger: device
        domain: carvera
        device_id: <pick in the UI>
        type: tool_change_required
    actions:
      - action: notify.mobile_app_your_phone
        data:
          title: "Carvera"
          message: >-
            Waiting for tool T{{ states('sensor.carvera_air_05214_target_tool') }}
            ({{ states('sensor.carvera_air_05214_job_file') }})
```

**Shop follows the machine:**

```yaml
  - alias: "Carvera powered on -> dust extraction outlet on"
    triggers:
      - trigger: state
        entity_id: binary_sensor.carvera_air_05214_online
        to: "on"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.dust_extractor
```

(Entity IDs contain your machine's name — pick them in the UI.)

## How the "usually off" handling works

The Carvera broadcasts a `NAME,IP,PORT,BUSY` announcement on UDP 3333 every second while powered on. The integration
listens passively: while no announcement is heard, it doesn't even attempt HTTP, so an off machine costs nothing.
When you flip the machine on, the announcement arrives within a second, the integration re-learns the machine's
current IP from it, and polling resumes. Everything except the **Online** sensor shows *unavailable* while the machine
is off — that's the correct, expected representation.

## Troubleshooting

**Nothing shows up in the discovery list.**
The machine is probably powered off (turn it on and retry), or UDP broadcasts on port 3333 don't reach your Home
Assistant (typical for Docker installs without host networking). Use *Enter address manually* — everything works
without discovery, you just lose the automatic IP-follow and the fast off-detection.

**"Could not reach the status API" during setup.**
The firmware feature is off. On the machine console (Carvera Controller or USB): `config-set sd wifi.http_enable true`
then `reset`. Verify with `curl http://<machine-ip>:8080/status` from any computer.

**All entities are unavailable.**
The machine is powered off — that's the intended representation. The **Online** binary sensor stays available and
tells you on/off; automate on that.

**Sensors freeze during file transfers.**
Expected: the firmware suspends its network stack while receiving a file (XMODEM). Everything recovers when the
transfer ends.

## Credits

Built on the Carvera Community Firmware's HTTP status API. Thanks to the
[Carvera-Community](https://github.com/Carvera-Community) project, and to tcatm's early webserver exploration that
paved the way.
