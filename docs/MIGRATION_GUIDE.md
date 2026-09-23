# Migration Guide: Moving from Legacy `foxess_modbus` to `foxess_modern`

## Acknowledgements

First and foremost, huge credit and gratitude go to **Nathan Marlor** and the open-source contributors of the original [`foxess_modbus`](https://github.com/nathanmarlor/foxess_modbus) integration. Nathan's pioneering reverse engineering, comprehensive register documentation, and dedication created the foundation that enabled thousands of FoxESS owners to integrate their solar hardware into Home Assistant. 

`foxess_modern` was designed to build upon that legacy by offering a high-performance, asynchronous Modbus client built directly on Home Assistant's modern architecture.

---

## Overview

When upgrading to `foxess_modern`, you can transition smoothly without losing any historical data, long-term statistics (LTS), energy dashboard cards, or custom automations.

Home Assistant associates historical recorder state data and Long-Term Statistics strictly by `entity_id` (for example, `sensor.foxess_battery_soc`). If a newly added sensor shares the same `entity_id` as your previous sensor, Home Assistant immediately attaches the incoming telemetry to your existing database records.

`foxess_modern` includes a built-in **Smart Sensor Mapping Wizard** that inspects your Home Assistant entity registry, detects legacy FoxESS entities, and pre-populates matching entity IDs automatically.

---

## Pre-Migration Checklist

1. **Avoid Port 502 Socket Conflicts**: Modbus TCP gateways (such as USR-TCP232, Waveshare, or Elfin devices) typically support only a single active TCP client connection at a time. If both `foxess_modbus` and `foxess_modern` attempt to connect concurrently, one or both integrations will experience socket timeouts.
2. **Disable the Legacy Integration First**: In Home Assistant, navigate to **Settings** > **Devices & Services**, find the legacy `foxess_modbus` card, click the three-dot menu, and choose **Disable**. This releases the network socket on your RS-485 adapter while retaining all entity IDs and historical records in the entity registry.

---

## Step-by-Step Migration Process

### Step 1: Install `foxess_modern`

Add `foxess_modern` to your Home Assistant instance via HACS (Custom Repository) or by copying the `custom_components/foxess_modern` directory into your Home Assistant `config/custom_components/` folder. Restart Home Assistant if required.

### Step 2: Add Integration and Enable Migration

1. Navigate to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for and select **FoxESS Modern**.
3. In the setup form, provide your connection details:
   - **Host**: IP address or hostname of your RS-485 gateway.
   - **Port**: Modbus TCP port (default: `502`).
   - **Modbus Slave ID**: Inverter slave address (default: `247`).
   - **Inverter Model**: Select your series (KH, H3, H3-Pro, or H1/AC1).
   - **Migrate entity IDs from legacy foxess_modbus integration**: Check this box. (Note: If Home Assistant detects existing legacy FoxESS entities, this option defaults to checked).
4. Click **Submit**. The integration verifies communication with the inverter.

### Step 3: Review Smart Sensor Mappings

Upon successful connection, the **Legacy Sensor Mapping Wizard** appears.

The wizard scans your Home Assistant entity registry for entities matching each metric:
- **Battery SoC**: defaults to `sensor.foxess_battery_soc` if present.
- **PV Power Total**: defaults to `sensor.foxess_pv_power` or `sensor.foxess_pv_power_total`.
- **PV1 and PV2 Power**: defaults to your existing string power sensors.
- **Grid CT Meter Power**: defaults to `sensor.foxess_feed_in_power` or `sensor.foxess_grid_ct_meter_power`.
- **House Load Power**: defaults to `sensor.foxess_load_power`.
- **Energy Dashboard Sensors**: automatically matches cumulative import, export, and battery energy entities.
- **Controls**: matches `select.foxess_work_mode` and `number.foxess_min_soc`.

For each sensor, you can:
- Accept the detected smart match.
- Pick a different existing entity from the dropdown.
- Select `(Default - Create New)` if you prefer generating a clean, standard entity ID.

Click **Submit** to finalize the configuration.

### Step 4: Verify History and Energy Dashboard

Once configured:
1. Open your Lovelace dashboards: cards referencing your mapped entity IDs will immediately resume updating with real-time data.
2. Check **History**: open any sensor detail modal (such as Battery SoC) and verify that historical curves and long-term statistics from before the migration remain intact.
3. Check the **Energy Dashboard**: because the cumulative kWh sensors maintain their entity IDs, your solar production, grid import/export, and battery metrics continue without gaps.

### Step 5: Clean Up Legacy Integration (Optional)

After verifying that all sensors are updating correctly and historical data is continuous:
- You may safely delete the disabled legacy `foxess_modbus` entry from **Settings** > **Devices & Services**.
- Deleting the disabled integration removes only the old integration registration; Home Assistant preserves your entity ID assignments and historical database statistics.

---

## Adjusting Mappings After Installation

If you need to change or fine-tune any entity mapping after initial setup:
1. Navigate to **Settings** > **Devices & Services**.
2. Locate the **FoxESS Modern** card and click **Configure**.
3. Adjust the sensor mappings in the options dialog and click **Submit**.
4. Home Assistant will automatically reload the integration with your updated mappings.

---

## Troubleshooting

### Socket Connection Error on Initial Setup
- Ensure the legacy `foxess_modbus` integration is disabled or stopped so port 502 on your RS-485 gateway is released.
- Verify the physical RS-485 connections on the inverter communication port (Pins 3 and 4 on 16-pin connectors, or Pins 1 and 2 on RJ45 connectors).

### Entity ID Has a `_2` Suffix
- If an entity was registered as `sensor.foxess_battery_soc_2`, Home Assistant detected that the original entity ID was still active.
- To resolve: disable or remove the legacy entity registration in **Settings** > **Devices & Services** > **Entities**, then edit the entity ID of the modern sensor to remove the `_2` suffix.

### Resolving Long-Term Statistics (LTS) Unit or Mean Type Repairs
If Home Assistant presents a repairs issue stating:
* *"The unit of sensor.xxx changed to 'W' which cannot be converted to the previously stored unit, 'kWh'"* or
* *"The mean type of sensor.xxx changed from 'None' to 'Arithmetic'"*

This occurs when a historical integration previously logged an entity with incompatible measurement types:
1. **Power Sensors** (`_power`): Strictly measured in **W** (watts) with arithmetic mean.
2. **Energy Sensors** (`_energy_total`): Strictly measured in **kWh** (kilowatt-hours) with sum accumulation.

To resolve:
1. Open **Settings** > **Developer Tools** > **Statistics**.
2. Locate the entity flagged with the issue (e.g., `sensor.battery_charge_power`).
3. Click **Fix Issue** and select **Delete all old statistic data for this entity** (or use the Repairs dialog `Delete` action).
4. Home Assistant will immediately clear the invalid legacy metadata and begin tracking clean, valid long-term statistics matching Home Assistant Core standards.

---

## Configuration Options

You can adjust the polling behavior at any time:
1. Navigate to **Settings** > **Devices & Services**.
2. Locate the **FoxESS Modern** card and click **Configure**.
3. **Readings Polling Interval**: Select your preferred scan frequency (5, 10, 15, 30, or 60 seconds; default is **15 seconds (Recommended)**).
4. **Reconfigure Legacy Mappings**: Check this box if you wish to adjust which legacy entity IDs are mapped to specific FoxESS metrics.
5. Click **Submit** to apply changes without restarting Home Assistant.
