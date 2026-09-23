# Predbat Integration Guide for FoxESS Modern

This guide explains how to integrate your FoxESS hybrid inverter with Predbat (battery prediction and automation software) using FoxESS Modern.

---

## 1. Overview

FoxESS Modern provides native, first-class telemetry and service controls designed specifically for automated battery management systems like Predbat.

Key features include:
* Native Signed Net Grid Power: Eliminates the need for custom Jinja2 template helpers. Positive values represent grid export, and negative values represent grid import.
* Remote Active Power Control: Direct charging and discharging via registers 44000 to 44002, preventing solar shedding.
* Native Service Calls: Dedicated services for force charging, force discharging, clearing overrides, and setting work modes.
* Full Model Range Scaling: Dynamic power limit scaling up to 30,000 W for commercial H3-Pro systems.

---

## 2. Preventing Solar Curtailment (Remote Active Power vs Work Mode)

A common challenge when automating FoxESS inverters with Predbat is solar curtailment (solar shedding):

* Traditional Work Mode Method: When automations switch the inverter work mode to "Back-up" to force grid charging, the inverter firmware isolates PV generation from domestic consumption. If rooftop solar generates power during the charging window, that energy is often throttled or shed rather than powering the house.
* FoxESS Modern Remote Control Method: FoxESS Modern utilizes the remote active power registers (registers 44000 to 44002). This commands the inverter to charge or discharge the battery at an exact target wattage while maintaining the primary work mode as "Self Use". Solar generation continues to supply household loads first, with excess solar supplementing the battery charge.

---

## 3. Required Entities

FoxESS Modern exposes all required entities directly. Replace `<serial>` with your inverter serial number or object ID prefix.

| Predbat Requirement | FoxESS Modern Entity | Description |
| :--- | :--- | :--- |
| **Battery State of Charge** | `sensor.<serial>_battery_soc` | Instantaneous battery percentage (0 to 100%) |
| **Battery Power** | `sensor.<serial>_battery_power` | Total battery power in Watts |
| **Battery Charge Power** | `sensor.<serial>_battery_charge_power` | Positive power flowing into the battery (Watts) |
| **Battery Discharge Power** | `sensor.<serial>_battery_discharge_power` | Positive power flowing out of the battery (Watts) |
| **Inverter Load Power** | `sensor.<serial>_house_load_power` | Instantaneous domestic consumption (Watts) |
| **PV Power Total** | `sensor.<serial>_pv_power_total` | Combined solar generation across all strings (Watts) |
| **Net Grid Power** | `sensor.<serial>_net_grid_power` | Signed grid power (+export, -import) in Watts |
| **Work Mode Selector** | `select.<serial>_work_mode` | Active inverter operating mode |
| **Min SoC Limit** | `number.<serial>_min_soc` | Inverter minimum reserve state of charge (%) |
| **Force Charge Power** | `number.<serial>_force_charge_power` | Maximum charge power setting (Watts) |
| **Force Discharge Power** | `number.<serial>_force_discharge_power` | Maximum discharge power setting (Watts) |

---

## 4. Predbat apps.yaml Configuration

Below is an example configuration for your `apps.yaml` file in Predbat:

```yaml
predbat:
  module: predbat
  class: Predbat

  # Inverter Configuration
  num_inverters: 1
  inverter_type: "FoxESS"

  # Telemetry Sensors (Replace <serial> with your inverter serial)
  soc_percent: sensor.<serial>_battery_soc
  battery_power: sensor.<serial>_battery_power
  load_power: sensor.<serial>_house_load_power
  pv_power: sensor.<serial>_pv_power_total

  # Native Signed Net Grid Power
  # FoxESS Modern provides: positive = export, negative = import
  grid_power: sensor.<serial>_net_grid_power

  # Control Entities
  work_mode: select.<serial>_work_mode
  battery_min_soc: number.<serial>_min_soc
  charge_rate: number.<serial>_force_charge_power
  discharge_rate: number.<serial>_force_discharge_power

  # Service Configuration for Remote Overrides
  # Using FoxESS Modern dedicated services ensures proper solar routing
  set_charge_service: "foxess_modern.set_force_charge"
  set_discharge_service: "foxess_modern.set_force_discharge"
  clear_service: "foxess_modern.clear_overrides"

  # Charging Constraints
  battery_capacity: 10.4 # Adjust to your installed battery kWh
  max_charge_power: 5000 # Adjust according to inverter and battery specs
  max_discharge_power: 5000
```

---

## 5. Available Service Actions

FoxESS Modern exposes 4 custom services that can be used in automations or called directly by Predbat:

### 5.1 foxess_modern.set_force_charge

Commands the inverter to force charge the battery from the AC grid.

```yaml
service: foxess_modern.set_force_charge
data:
  device_id: "KH10ABC1234567" # Optional if only one inverter is installed
  power: 3500                  # Target charge power in Watts (100 to 30000)
  max_soc: 100                 # Target maximum State of Charge percentage (10 to 100)
  duration: 3600               # Override duration in seconds (60 to 86400)
```

### 5.2 foxess_modern.set_force_discharge

Commands the inverter to force export battery power to domestic loads or grid.

```yaml
service: foxess_modern.set_force_discharge
data:
  device_id: "KH10ABC1234567"
  power: 4000                  # Target discharge power in Watts (100 to 30000)
  min_soc: 15                  # Minimum reserve State of Charge percentage (10 to 100)
  duration: 1800               # Override duration in seconds (60 to 86400)
```

### 5.3 foxess_modern.clear_overrides

Cancels any active remote power override and restores normal autonomous Self-Use operation.

```yaml
service: foxess_modern.clear_overrides
data:
  device_id: "KH10ABC1234567"
```

### 5.4 foxess_modern.set_work_mode

Sets the inverter primary operating mode directly.

```yaml
service: foxess_modern.set_work_mode
data:
  device_id: "KH10ABC1234567"
  work_mode: "Self Use" # Options: "Self Use", "Feed-in First", "Back-up"
```
