# Polish Shipment Tracking

Polska wersja: [README.md](README.md)
![Shipment Tracking card](screenshot.png)


[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Home Assistant integration for tracking shipments from popular carriers in Poland. It creates sensor entities for active shipments and includes a Lovelace card with a list of shipments.

## Features

- Multiple carriers supported in a single integration (Config Flow)
- Sensor entities for active shipments
- Status normalization into a common set of states
- Automatic discovery of new shipments and cleanup of old entities
- Built-in Lovelace card:
  - served by the integration
  - automatic resource registration for storage dashboards

> [!TIP]
> You can add multiple entries for the same carrier (e.g., your number and your spouse's account).

## Supported carriers

- InPost
- DHL
- DPD
- Pocztex

> [!WARNING]
> The integration relies on unofficial APIs used by carrier apps/services. These APIs may change without notice.

> [!CAUTION]
> I am not responsible if a carrier blocks or limits a user account in any way.


## Requirements

- Home Assistant 2024.6 or newer
- (Optional) HACS 1.30 or newer

## Installation

### HACS (recommended)

1. Open HACS -> Integrations.
2. Add this repository as a Custom repository:
   - Repository: https://github.com/stirante/polish_shipment_tracking
   - Category: Integration
3. Install the integration.
4. Restart Home Assistant.

### Manual install

1. Copy `custom_components/polish_shipment_tracking` into:
   `<config>/custom_components/polish_shipment_tracking`
2. Restart Home Assistant.

## Configuration

1. Settings -> Devices and Services -> Add Integration
2. Search for "Polish Shipment Tracking"
3. Pick a carrier and provide the required credentials
4. Save

Sensor entities should appear after the first refresh.

## Entities

The integration creates one `sensor` per active (not delivered) shipment.

- unique_id: `<courier>_<shipment_id>`
- sensor state: normalized status (for example: in_transport)
- attributes: carrier-specific, commonly:
  - shipment number
  - raw status
  - event history
  - event timestamps
  - pickup point details

## Status normalization

Carrier-specific status names are mapped to a common set, for example:
- created
- in_transport
- waiting_for_pickup
- delivered
- exception
- unknown

> [!NOTE]
> Status mapping is not complete yet; PRs with new mappings are welcome.

See the implementation in the integration code (sensor.py).

## Lovelace card


The integration bundles a Lovelace card (JavaScript module) and will automatically add it to Lovelace Resources.

## Debugging

Enable debug logs:

```yaml
logger:
  default: info
  logs:
    custom_components.polish_shipment_tracking: debug
```

## Known issues

* Carrier API/auth changes can break login or tracking.

## Issues and support

* Issues: [https://github.com/stirante/polish_shipment_tracking/issues](https://github.com/stirante/polish_shipment_tracking/issues)
* Pull requests are welcome.

When reporting a bug, include:

* Home Assistant version
* logs (with debug enabled)
* selected carrier
* reproduction steps

## License

GNU General Public License v3.0. See LICENSE.
