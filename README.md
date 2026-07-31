# MakerHA — Makera Carvera for Home Assistant

*Makera yourself at home.*

Local, no-cloud Home Assistant integration for [Makera Carvera](https://www.makera.com) CNC machines running the
[Community Firmware](https://github.com/Carvera-Community/Carvera_Community_Firmware) with the read-only HTTP status API.

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

1. HACS → three-dot menu → **Custom repositories** → add `https://github.com/BellionBastien/MakerHA` as type *Integration*.
2. Search for **MakerHA**, download, restart Home Assistant.
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

## Credits

Built on the Carvera Community Firmware's HTTP status API. Thanks to the
[Carvera-Community](https://github.com/Carvera-Community) project, and to tcatm's early webserver exploration that
paved the way.
