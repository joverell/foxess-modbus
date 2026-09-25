# FoxESS Modbus Hardware Setup, Wiring & Field Observations Guide

A comprehensive, field-tested guide for interfacing **FoxESS Hybrid Inverters** (KH, H1, H3, and H3-Pro series) with Home Assistant via RS-485 Modbus bridges (such as the Waveshare RS485-to-Ethernet/Wi-Fi Gateway).

---

## 1. Overview & Communication Architecture

FoxESS inverters expose internal metrics (PV generation, battery state, grid import/export) and control parameters (Work Mode, Min SoC, Force Charge/Discharge) over standard half-duplex **RS-485 Modbus RTU**.

To integrate the inverter with Home Assistant without cloud dependence, an industrial RS-485 to Ethernet/Wi-Fi gateway translates between network packets (**Modbus TCP**) and serial signals (**Modbus RTU**).

```text
+-------------------+             Modbus TCP             +--------------------------+
|   Home Assistant  | <================================> | Waveshare / USR Gateway  |
|  (foxess_modern)  |        (Port 502 / TCP or UDP)     | (High-Flying HF-A11 SoC) |
+-------------------+                                    +--------------------------+
                                                                      ||
                                                              RS-485 Half-Duplex
                                                              (A+, B-, GND / 9600 Baud)
                                                                      ||
                                                         +--------------------------+
                                                         |      FoxESS Inverter     |
                                                         |   AUX Port (Slave 247)   |
                                                         +--------------------------+
```

---

## 2. Inverter Physical Port Pinouts: AUX vs. METER

Depending on your specific FoxESS inverter series and hardware revision, communication wiring is terminated either via a standard **RJ45 port** or a **16-pin push-in terminal plug**.

### 2.1 RJ45 Modular Connector Option

Found on H1, H3, H3-Pro, and certain KH revisions:

```text
RJ45 Connector Pinout (Pin 1 on far left, clip facing down/away):
 _________________________________________
|  1  |  2  |  3  |  4  |  5  |  6  |  7  |  8  |
|  A  |  B  | GND |  -  |  -  |  -  | GND |  -  |
|_____|_____|_____|_____|_____|_____|_____|_____|
```

| Inverter Series | Recommended Port | Pin 1 | Pin 2 | Pin 3 / 7 | Role | Modbus Unit ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **KH Series** (KH7 to KH10.5) | **AUX** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | **Slave** (Passive) | **247** |
| **H1 / AC1 Series** | **COM** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | **Slave** (Passive) | **247** |
| **H3 / AC3 Series** | **RS485** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | **Slave** (Passive) | **247** |
| **H3-Pro Series** | **RS485 / COM** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | **Slave** (Passive) | **247** |

---

### 2.2 16-Pin Multi-Connector Plug (KH Series)

Many KH hybrid installations use a multi-pin push-in connector (black body with orange spring-release buttons) on the underside of the inverter:

```text
16-Pin Communication Plug (Looking directly at connector face):

TOP ROW:     [ 1 ]        [ 2 ]        [ 3 ]        [ 4 ]        [ 5 ]
          Meter485A    Meter485B       485B         485A         CT2+
           (Master)     (Master)     (Slave B-)   (Slave A+)
                                         │            │
                                  [To Waveshare] [To Waveshare]
                                       B/R          A/T

MIDDLE ROW:  [ 11 ]       [ 10 ]       [ 9 ]        [ 8 ]        [ 7 ]        [ 6 ]
              K2           K1           /           CT1+         CT1-         CT2-
                                                  (Grid CT)    (Grid CT)
                                                     │            │
                                                [To CT Clamp] [To CT Clamp]

BOTTOM ROW:  [ 12 ]       [ 13 ]       [ 14 ]       [ 15 ]       [ 16 ]
              K3           K4           /            DI          COM
```

| Pin | Function | Hardware Role | Destination / Cable Connection |
| :--- | :--- | :--- | :--- |
| **1** | `Meter485A` | Inverter Master (RS-485 Data+) | Physical energy meter (e.g. DDSU666 / SDM230) |
| **2** | `Meter485B` | Inverter Master (RS-485 Data-) | Physical energy meter (e.g. DDSU666 / SDM230) |
| **3** | **`485B`** | **Inverter Slave (RS-485 Data-)** | **Waveshare `B/R` terminal** (Home Assistant) |
| **4** | **`485A`** | **Inverter Slave (RS-485 Data+)** | **Waveshare `A/T` terminal** (Home Assistant) |
| **5** | `CT2+` | Secondary CT (Positive) | Optional second solar inverter clamp |
| **6** | `CT2-` | Secondary CT (Negative) | Optional second solar inverter clamp |
| **7** | **`CT1-`** | **Grid CT Clamp (Negative)** | **Main grid CT clamp** |
| **8** | **`CT1+`** | **Grid CT Clamp (Positive)** | **Main grid CT clamp** |
| **9–16** | Relay / DRM / DI | Control Signals | Demand response (DRM) or heat pump contacts |

#### Multi-Conductor Cable Terminations
Installers frequently route a single multi-conductor cable between the switchboard and the inverter:
* **Pins 7 & 8:** Dedicated to the grid CT clamp for load measurement.
* **Pins 3 & 4:** Dedicated to the RS-485 Modbus bridge for Home Assistant communication.

Even when these pairs share the same outer cable sheath, they terminate at completely separate, electrically isolated pin positions on the plug.

---

### 2.3 The Critical Port Distinction: Why Meter Pins Will Fail

> [!CAUTION]
> **DO NOT connect your Home Assistant gateway to the Meter pins (Pins 1 & 2).**
>
> * **Meter Port = Hardware Master:** The FoxESS internal CPU is programmed in firmware to act as an RS-485 Master on the Meter pins. It continuously broadcasts polling frames every 100 to 200 ms to read an external energy meter.
> * **Electrical Bus Collisions:** RS-485 (EIA-485) supports only one master at a time. If you wire your Home Assistant bridge into Pins 1 & 2, Home Assistant and the Inverter CPU will both drive signals onto the same copper pair at the same time. This creates electrical signal collisions, corrupted checksums, and communication fault alarms on the inverter display.
> * **AUX / 485 Pins = Hardware Slave (Unit ID 247):** Pins 3 & 4 (or the dedicated AUX RJ45 port) operate as a Modbus Slave. The inverter remains silent and only responds when spoken to by Home Assistant.

#### What About Multiple Slaves on the AUX Bus?
If you have multiple Modbus slave devices (e.g., an Eastron meter on Slave ID 1 and the FoxESS inverter on Slave ID 247) sharing the same RS-485 gateway, Home Assistant's native connection broker (`modbus-connection`) sequences all requests cleanly, preventing collisions between integrations.

---

## 3. Waveshare RS485-to-Ethernet/Wi-Fi Gateway Setup

This section applies to the popular **Waveshare RS485 to Ethernet/WiFi Gateway** (and functionally identical High-Flying HF-A11 / USR-W610 hardware).

### Step 1: Initial Connection
1. Power the module using a 9–36V DC supply (or 5V micro-USB depending on hardware revision).
2. The device broadcasts an initial Wi-Fi hotspot: `Waveshare_E600` (or `HF-A11x_AP`).
3. Connect your computer to this hotspot and navigate to the web management console at:
   ```text
   http://10.10.100.254
   ```
4. Default credentials:
   * **Username:** `admin`
   * **Password:** `admin`

---

### Step 2: Serial & Modbus Protocol Conversion
Navigate to **Wifi-Uart Setting** in the web interface:

1. **Serial Port Settings:**
   * **Baud Rate:** `9600` *(standard for FoxESS AUX/COM; LAN firmware builds may use 115200)*
   * **Data Bits:** `8`
   * **Parity:** `None`
   * **Stop Bits:** `1`
   * **Flow Control:** `None`

2. **Modbus Protocol Conversion (CRITICAL):**
   * Locate **Data Transfer Mode** or **Modbus Polling Settings**.
   * Change from `Transparent / Passthrough` to **`Modbus TCP <=> Modbus RTU`** (or turn **Modbus Polling** `ON`).
   * *Why:* This instructs the onboard processor to strip incoming network TCP headers, generate valid 16-bit Modbus RTU CRC checksums before transmitting over RS-485, and wrap returning serial frames back into Modbus TCP packets for Home Assistant.

3. **Network A Settings:**
   * **Mode:** `Server`
   * **Protocol:** `TCP` *(see Section 6 for UDP fallback)*
   * **Port:** `502` *(standard Modbus TCP port)*
   * Click **Apply**.

4. **Disable Unused Background Sockets:**
   * **Socket B:** Set to `OFF` and click **Apply**.
   * **MQTT Settings:** Set to `OFF` and click **Apply**.
   * *Why:* Disabling unused cloud sockets prevents memory contention and packet buffering delays on the bridge's microcontroller.

---

### Step 3: Wi-Fi STA Configuration
1. Navigate to **STA Interface Setting**.
2. Enable Station mode, select your home Wi-Fi SSID, and enter your WPA2/WPA3 passphrase. Click **Apply**.
3. Navigate to **Mode Selection** and change the operating mode from `AP Mode` to **`STA Mode`** (or `AP+STA Mode` for initial safety). Click **Apply**.
4. Navigate to **Device Management**, scroll down, and click **Restart**.
5. The device will reboot and join your home network. Check your home router’s DHCP client list to find the adapter's assigned local IP address (e.g. `192.168.86.162`).

---

## 4. Field Observations: The Inverter Lockup Case Study

During field testing on a FoxESS KH10 installation, a critical hardware interaction was discovered when using aggressive polling or write operations over Wi-Fi.

### The Progression of Failure
1. **The Lockup:** Home Assistant was connected via a Wi-Fi gateway. After attempting to write inverter parameters (such as changing Work Mode or Min SoC), all entities suddenly flipped to `Unavailable`.
2. **The Timeout Loop:** Home Assistant logs began flooding with continuous errors:
   ```text
   modbus_connection: Error reading registers: Timeout after 5.0s on unit 247
   ```
3. **Failed Soft Fixes:**
   * **Home Assistant Reload:** Reloading the integration had no effect.
   * **Gateway Web GUI Reboot:** Clicking "Restart" inside the Waveshare web interface had no effect. The gateway came back online, but the inverter still refused to answer on Port 502.
   * **The Inverter AC Breaker Trap:** Flicking the AC solar breaker in the switchboard did **not** reboot the inverter. The inverter’s screen remained lit, and internal processing continued uninterrupted because the logic board remained powered by the **DC Solar Arrays** and the **High-Voltage Battery**.
4. **The Ultimate Recovery (Full Cold Reboot):**
   * The only action that restored communication was an alarming, full cold shutdown of the entire system (AC breaker off, PV DC isolator off, and Battery BMS power switched off until all LEDs went dark). Once power was restored, communication resumed immediately.

### The Architectural Root Cause
Inside the FoxESS inverter, the AUX communication port is managed by a secondary low-power microcontroller with a small hardware UART FIFO buffer (typically 64 bytes).
* When an integration floods the bus with rapid, unbatched register reads, or sends a write command while the buffer is saturated, the **inverter's UART driver enters a hardware deadlock state**.
* The communications MCU halts serial processing until it experiences a true physical power drop.

---

## 5. The Two-Tier Power-Cycle Guide

If your FoxESS Modbus communication stops responding, use this tiered approach:

### Tier 1: Gateway Cold Reset (Adapter Transceiver Clear)
The serial transceiver chip (MAX485/SP3485) on Waveshare and USR gateways can retain volatile UART latch-up states across web GUI soft restarts.
1. **Physically unplug the DC power jack or terminal block** feeding the Waveshare gateway.
2. Leave it disconnected for **10 seconds**.
3. Plug it back in.
4. If communication resumes, the issue was a latched gateway transceiver.

---

### Tier 2: Full Inverter & Battery Cold Restart (Inverter MCU Reset)
If the gateway is reachable on port 502 but the inverter returns continuous timeouts, the FoxESS AUX microcontroller has frozen. Because the inverter draws power from three independent sources (AC, PV, Battery), you must perform a full cold shutdown:

```text
SHUTDOWN SEQUENCE:
[1. AC Grid]      Switch OFF the Inverter AC Circuit Breaker in the switchboard.
        ↓
[2. Solar PV]     Rotate the Inverter DC Isolator switch to OFF (O).
        ↓
[3. Battery BMS]  Switch OFF the Battery BMS isolator switch and press/hold 
                  the battery power button until all LED indicator rings turn completely dark.
        ↓
[4. Drain]        WAIT 60 SECONDS. Allow internal capacitors to fully discharge 
                  until the inverter LCD screen is completely blank.

STARTUP SEQUENCE (REVERSE ORDER):
[1. Battery BMS]  Turn ON the Battery BMS isolator switch and press the power button.
                  Wait for the BMS contactor to click and the battery LEDs to stabilize.
        ↓
[2. Solar PV]     Rotate the Inverter DC Isolator switch to ON (I).
        ↓
[3. AC Grid]      Switch ON the Inverter AC Circuit Breaker in the switchboard.
```

---

## 6. How `foxess_modern` Safeguards Inverter Communication

To maintain high reliability across different network environments (especially over wireless bridges or noisy multi-core cable runs), `foxess_modern` adopts the architectural patterns established in [Modernizing Modbus in Home Assistant](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/):

1. **Defensive Register Grouping (`max_span = 8`):**
   * Rather than issuing dozens of separate single-register queries, `foxess_modern` groups contiguous registers into compact spans capped at 8 registers.
   * Telemetry is gathered in small, predictable transactions. This keeps the serial bus clear and strictly prevents buffer saturation on FoxESS AUX UART microcontrollers or latency-prone wireless bridges.
   * Note: While certain hardwired, direct-serial installations might technically tolerate wider spans, limiting transactions to 8 registers represents a proven, defensive standard that ensures complete immunity from microcontroller serial lockups across all FoxESS hardware revisions.

2. **Inter-Frame Timing Safeguards (`message_spacing = 250ms`):**
   * Enforces a 250 ms (`0.25s`) rest interval between consecutive Modbus transactions, giving the inverter AUX microcontroller and the gateway transceiver sufficient decay time to clear their receive buffers.

3. **Coordinated Write Locking (`modbus-connection`):**
   * All read and write operations pass through Home Assistant's central asynchronous queue broker.
   * When an automation or UI entity updates a setting (such as Work Mode or Min SoC), the broker waits for any active read transaction to complete, holds subsequent reads, and executes the write cleanly. This prevents packet collisions on the half-duplex line.

4. **Staggered Polling Cycles:**
   * Dynamic operational readings (power, voltage, SoC) poll every 15 seconds (`SCAN_INTERVAL = 15`).
   * Configuration parameters (configured Min SoC, charge windows) poll every 60 seconds (`SETTINGS_SCAN_INTERVAL = 60`).

5. **Universal Coordinator Debouncing:**
   * Wireless gateways located near switchboards or outdoor meter boxes experience occasional dropped Wi-Fi packets or TCP retransmission jitter.
   * Inverter data in memory remains valid across transient timeouts. Coordinators debounce single poll failures (`self._timeouts < 2 and self.data is not None`), preventing entities like `Export Power Limit`, `Min SoC`, or `Work Mode` from flapping to `Unavailable` during isolated packet drops, while still recycling wedged bridge connections if 3 consecutive timeouts occur.

---

## 7. Switchboard Wi-Fi (Faraday Cage) & Modbus UDP Fallback

### The Faraday Cage Effect
Inverters and gateways are commonly installed inside metal meter boxes or switchboards.
* A grounded metal enclosure acts as a **Faraday cage**, drastically attenuating 2.4 GHz Wi-Fi signals.
* High packet loss and Wi-Fi latency cause TCP retransmission storms, which buffer up and delay Modbus frames.

**Mitigation Options:**
1. **External Dipole Antenna:** If using a Wi-Fi gateway, route an antenna extension cable outside the metal box and mount the rubber-duck antenna externally.
2. **Powerline Bridge:** Use a Powerline (HomePlug AV2) adapter to bring Ethernet directly into the switchboard.
3. **Hardwired Ethernet (Best):** Run a dedicated Cat5e/Cat6 cable to the gateway.

---

### Modbus UDP Fallback
If you must use Wi-Fi and experience periodic TCP connection resets or timeout loops, switching to **Modbus UDP** can resolve the issue:
* Unlike TCP (which requires 3-way handshakes and retransmission retries), UDP is connectionless and does not stall when individual packets drop.
* High-Flying / Waveshare firmware handles Modbus UDP on port 502 with significantly lower CPU overhead.

**To Switch to UDP:**
1. In the Waveshare web GUI (**Wifi-Uart Setting** → **Network A Setting**):
   * Change **Protocol** from `TCP` to `UDP`.
   * Keep **Port** at `502`.
   * Click **Apply** and perform a 10-second power-cycle.
2. In Home Assistant:
   * Delete or reconfigure the integration entry and select UDP protocol targeting port 502.

---

## 8. Home Assistant UI Setup (`foxess_modern`)

1. In Home Assistant, navigate to **Settings → Devices & Services → Add Integration**.
2. Search for **FoxESS Modern** (or click the My Home Assistant badge in the README).
3. Complete the single-screen configuration form:

| Field | Recommended Value | Description |
| :--- | :--- | :--- |
| **Host** | `192.168.86.162` | Local IP address or hostname of your Waveshare bridge |
| **Port** | `502` | Modbus TCP port (standard default) |
| **Inverter Slave ID** | `247` | FoxESS AUX port factory default Unit ID |
| **Inverter Model** | `KH10`, `H3-Pro`, `H3`, or `H1` | Select your inverter model family |

4. Click **Submit**. Home Assistant’s connection broker will immediately probe Unit ID 247 on your bridge using `async_get_temporary_unit`. If valid readings are returned, the device and all associated sensor entities will be created immediately.

---

## 9. Multi-Device RS-485 Bus Sharing with Core Modbus

If you connect multiple Modbus slave devices to the same physical RS-485 gateway (for example, the FoxESS Inverter on Slave ID 247, an Eastron SDM630 Grid Meter on Slave ID 1, and an EV Charger on Slave ID 2), having separate integrations open independent TCP connections causes serial collision errors on the half-duplex wire.

To enable centralized connection pooling and serial bus locking across multiple integrations, configure a shared Modbus gateway hub in `configuration.yaml`:

```yaml
modbus:
  - name: "waveshare_gateway"
    type: tcp
    host: 192.168.86.162
    port: 502
    timeout: 5
    message_wait_milliseconds: 250
```

### Automatic Promotion in `foxess_modern`
* When `modbus:` is present in `configuration.yaml`, `foxess_modern` automatically detects the shared gateway on startup and leases Slave ID 247 from Core Modbus.
* If `modbus:` is not configured in YAML, `foxess_modern` runs seamlessly in standalone mode using its internal `modbus-connection` transport with zero manual configuration required.

---

## 10. External References & Sourced Documentation

* [Waveshare RS485 TO ETH / WIFI User Manual & Wiki](https://www.waveshare.com/wiki/RS485_TO_ETH)
* [Home Assistant Modbus Integration Documentation](https://www.home-assistant.io/integrations/modbus/)
* [Home Assistant Developer Blog: Modernizing Modbus (Core 2026.7+)](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/)
* [modbus-connection Python Library Reference](https://home-assistant-libs.github.io/modbus-connection/)
* [FoxESS KH Series Single-Phase Hybrid Inverter User Manual](https://www.fox-ess.com/)

