# Heatit WiFi6 Thermostat for Home Assistant

Home Assistant integration for Heatit WiFi6 floor heating thermostats, talking
to the device's own local HTTP API. No cloud, no MyHeatit account.

Covers all 25 writable parameters and all five endpoints of the Heatit
"WiFi 6" API v7.0.0.

## Disclaimer

This is a third-party integration. It is not affiliated with, endorsed by, or
supported by Heatit Controls / Thermo-Floor AS. "Heatit" and the Heatit logo are
trademarks of their respective owner, used here only to identify the hardware
this integration talks to.

## Supported devices

- Heatit WiFi6 thermostat

Developed and tested against firmware **2.26**. Other versions should work but
are untested; the same 42 entities are always created, and any the firmware does
not report simply stay empty.

Requires Home Assistant **2026.9** or newer, and the thermostat reachable on
your local network.

> Not to be confused with Home Assistant's official **Heatit** integration,
> which supports the Z-Wave range (Z-TRM, Z-Temp, Z-Push). This one is for the
> WiFi6 thermostat and does not use Z-Wave.

## Installation

### HACS

1. Make sure [HACS](https://hacs.xyz/) is installed.
2. Open **HACS** in Home Assistant.
3. Click the three dots in the top right and choose **Custom repositories**.
4. Paste `https://github.com/tuomaskuittinen/heatit-wifi-thermostat`, set the
   type to **Integration**, and click **Add**.
5. Search for **Heatit WiFi6 Thermostat** and download it.
6. Restart Home Assistant.

### Manual

1. Download this repository.
2. Copy its contents - the files themselves, not a nested folder - into
   `config/custom_components/heatit_wifi_thermostat/`.
3. Restart Home Assistant.

## Setup

1. Set the thermostat up on your WiFi network using the official Heatit mobile
   app. This integration talks to the device locally, but the thermostat has to
   be on the network before Home Assistant can reach it.
2. Give it a fixed address — a DHCP reservation on your router is easiest.
3. In Home Assistant go to **Settings → Devices & Services → Add Integration**.
4. Search for **Heatit WiFi6 Thermostat**.
5. Fill in the fields below and submit.
6. Repeat for each thermostat.

| Field | |
|---|---|
| **IP address or hostname** | e.g. `10.0.0.50`. The `http://` prefix is added if you leave it out. |
| **Name** | Becomes the device name and drives the entity IDs, so `Bathroom` gives `sensor.bathroom_floor_temperature`. Worth getting right: renaming later does not rename existing entity IDs. |

The address can be changed later with **Reconfigure**, which keeps all entities
and their history. Reconfigure refuses an address belonging to a different
thermostat, so an entry can never be silently rebound to the wrong unit.

> The device's own `name` and `room` come from the MyHeatit app. They are blank
> on units the app has never written to, space-stripped when they are set, and
> manufacturer firmware updates have been observed clearing them. That is why
> the name is asked for here rather than read from the device. Leaving it blank
> falls back to that stored name, or to `Heatit Thermostat` when there is none.

## Entities

**42 entities per thermostat**, 13 of them disabled by default. Configuration
and diagnostic entities are tagged as such, so they stay off your dashboards.

### Climate

`climate.<name>` — off / heat / cool, with an **eco** preset for the device's
fourth operating mode. `hvac_action` reflects the device's own relay state.

**The current temperature follows Sensor Mode.** In floor sensor mode the card
shows the floor reading, in internal mode the internal one, in either external
mode the external one — because that is the sensor the thermostat regulates on,
and the setpoint is a value for that same sensor. The min/max bounds follow the
matching limit pair for the same reason. Change Sensor Mode and both change with
it; all three temperatures remain available as separate sensors regardless.

### Sensor

| Entity | Value | Enabled |
|---|---|---|
| Internal Temperature | °C | yes |
| Floor Temperature | °C | yes |
| External Temperature | °C | no |
| Power Consumption | W | yes |
| Total Consumption | kWh, works in the Energy dashboard | yes |
| Thermostat State | Idle / Heating / Cooling | yes |
| Open Window Time Remaining | seconds | no |
| Firmware Version | | yes |
| Device Name | the MyHeatit name stored on the device | yes |
| Room | the MyHeatit room stored on the device | yes |
| WiFi Signal Strength | dBm | no |
| SSID | | no |
| IP Address | | no |
| MAC Address | | no |

### Binary sensor

| Entity | Value | Enabled |
|---|---|---|
| Window Detection | Open while the device has detected a window and lowered the setpoint | yes |

### Number

| Entity | Range | Enabled |
|---|---|---|
| Heating Setpoint | 5 to 40 °C, step 0.5 | yes |
| Cooling Setpoint | 5 to 40 °C, step 0.5 | yes |
| ECO Setpoint | 5 to 40 °C, step 0.5 | yes |
| Internal Minimum Temperature | 5 to 40 °C, step 0.5 | yes |
| Internal Maximum Temperature | 5 to 40 °C, step 0.5 | yes |
| Floor Minimum Temperature | 5 to 40 °C, step 0.5 | yes |
| Floor Maximum Temperature | 5 to 40 °C, step 0.5 | yes |
| External Minimum Temperature | 5 to 40 °C, step 0.5 | no |
| External Maximum Temperature | 5 to 40 °C, step 0.5 | no |
| Internal Calibration | -6 to 6 °C, step 0.1 | yes |
| Floor Calibration | -6 to 6 °C, step 0.1 | yes |
| External Calibration | -6 to 6 °C, step 0.1 | no |
| Temperature Control Hysteresis | 0.3 to 3 °C, step 0.1 | yes |
| Active Display Brightness | 1 to 10 | yes |
| Standby Display Brightness | 1 to 10 | yes |
| Size Of Load | 0 to 9900 W, step 100 | yes |
| Power Regulator Active Time | 10 to 100 %, step 10 | no |
| Auto-retry Delay After Error | 0 to 65535 s | no |

### Select

| Entity | Options | Enabled |
|---|---|---|
| Sensor Mode | Floor sensor / Internal sensor / Internal with floor limitation / External sensor / External with floor limitation / Power regulator mode | yes |
| Regulation Mode | Hysteresis / PWM | yes |
| Temperature Display | Setpoint / Measured temperature | yes |
| Sensor Resistance | 10, 12, 15, 22, 33, 47, 6.8 or 100 kOhm | no |

### Switch

| Entity | Enabled |
|---|---|
| Disable Buttons | yes |
| Open Window Detection | yes |

### Button

| Entity | Enabled |
|---|---|
| Reset Energy Meter | yes |
| Reset Settings | no |

### Polling and availability

The thermostat is polled once a minute, so a change made at the physical
thermostat can take up to a minute to appear in Home Assistant. Changes made
*from* Home Assistant appear immediately: the device confirms each write, and
that value is held for up to 30 seconds because `/api/status` keeps serving the
previous one for several seconds afterwards.

If the thermostat becomes unreachable all of its entities go unavailable
together, and recover on the next successful poll. A write that fails raises an
error naming the device rather than failing silently.

**Download diagnostics** on the device page dumps the full device response with
the address, MAC, SSID and device id redacted — the most useful thing to attach
to a bug report.

## Actions

### `heatit_wifi_thermostat.factory_reset`

Full factory reset of one thermostat. This is an action rather than a button
because it **erases the WiFi credentials** — the device leaves the network and
has to be re-onboarded through the MyHeatit app with physical access to the
unit. Requires `confirm: reset`.

```yaml
action: heatit_wifi_thermostat.factory_reset
data:
  device_id: <the thermostat's device id>
  confirm: reset
```

The gentler `Reset Settings` button returns every parameter to its factory
default while keeping the WiFi credentials.

## Notes on the risky settings

This integration deliberately exposes everything the device exposes. A few
settings can affect hardware, so they are worth understanding:

- **Floor Maximum Temperature** is the floor protection limit. The API allows up
  to 40 °C; your flooring may not.
- **Floor Calibration** shifts what the device believes the floor temperature is,
  so a large offset overshoots the maximum limit by the same amount.
- **Sensor Mode → Power regulator mode** runs a fixed duty cycle with **no
  temperature feedback and no floor limit** — those apply only to the other five
  modes. At **Power Regulator Active Time** 100% the relay never opens.
- **Auto-retry Delay After Error** at a non-zero value makes the device re-close
  the relay into an overload or overheat fault on a timer, indefinitely. The
  default of 0 means "stay off and show an error".

The last two are disabled by default.

## API reference

Every range, enumeration and default in this integration comes from Heatit's
"WiFi 6" HTTP API specification, version 7.0.0, published by Heatit at:

- Swagger UI — <https://documents.heatit.no/5430542/api>
- Raw OpenAPI YAML — <https://media.heatit.com/4147?type=direct>

Both serve the same document, so it is not reproduced here. Should those links
move, the exact file is 34993 bytes, sha256
`29092d5496aaaf5c273b269aa5f0391afb42d6665a30758f40d3e09a9e0f4094`.

### Firmware differences

Two documented fields were never seen on firmware 2.26, so both are treated as
optional: `network.status`, which is not exposed at all, and
`parameters.OWD.activeTime`, the seconds remaining before open window detection
releases the setpoint. The latter is absent whenever detection is idle and may
only appear once a window is actually detected — untested against a real
detection event, so `Open Window Time Remaining` is created but disabled by
default.

## Language support

English and Finnish (`fi`).

Select option values (sensor mode, regulation mode, temperature display, sensor
resistance) stay in English in every language, because automations pick them by
their literal text.

## Changelog

### 1.0.0

First release.

## License

MIT — see [LICENSE](LICENSE).
