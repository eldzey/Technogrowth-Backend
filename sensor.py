"""
sensor_reader.py — TechnoGrowth · Raspberry Pi 5 Sensor Reader (Full Fixed)
=============================================================================
Reads real hardware sensors, controls relays, and POSTs data to Flask backend.

Wiring Guide:
─────────────────────────────────────────────────────────────────────────────
Sensor            GPIO Pin    Notes
─────────────────────────────────────────────────────────────────────────────
DHT22 (Temp/Hum)  GPIO 4      Data → GPIO4, VCC → 3.3V, 10kΩ pull-up required
Soil Moisture     GPIO (SPI)  Analog via MCP3008 CH0 (SPI bus 0, CE0)
NPK Sensor        /dev/ttyUSB0  RS-485 via USB adapter, Modbus RTU @ 4800 baud
Relay Pump        GPIO 27     Active-LOW relay (LOW = pump ON)
Relay Fan         GPIO 22     Active-LOW relay (LOW = fan ON)
─────────────────────────────────────────────────────────────────────────────

MCP3008 SPI Wiring:
  MCP3008 VDD  → 3.3V      MCP3008 CLK  → GPIO 11 (SCLK)
  MCP3008 VREF → 3.3V      MCP3008 DOUT → GPIO 9  (MISO)
  MCP3008 AGND → GND       MCP3008 DIN  → GPIO 10 (MOSI)
  MCP3008 DGND → GND       MCP3008 CS   → GPIO 8  (CE0)
  Moisture sensor OUT → MCP3008 CH0

Install dependencies on Pi 5:
  sudo apt-get install -y libgpiod2 python3-pip
  pip install adafruit-circuitpython-dht RPi.GPIO spidev requests \
              python-dotenv pyserial

Enable SPI: sudo raspi-config → Interface Options → SPI → Enable
Enable Serial: sudo raspi-config → Interface Options → Serial Port → Enable
  (Disable login shell over serial, keep serial port hardware enabled)

Run as service (recommended):
  sudo cp technogrowth-sensor.service /etc/systemd/system/
  sudo systemctl enable technogrowth-sensor
  sudo systemctl start technogrowth-sensor
"""

import time
import logging
import logging.handlers
import requests
import os
import random
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════
FLASK_URL         = os.getenv("FLASK_URL", "http://localhost:5000")
POLL_INTERVAL     = int(os.getenv("POLL_INTERVAL", "30"))   # seconds (DHT22 needs ≥5s; 30s is reliable)
COMMAND_POLL_INTERVAL = 5    # seconds between manual command checks

TEMP_OPTIMAL_MIN  = float(os.getenv("TEMP_MIN",  "25.0"))
TEMP_OPTIMAL_MAX  = float(os.getenv("TEMP_MAX",  "30.0"))
MOIST_OPTIMAL_MIN = float(os.getenv("MOIST_MIN", "43.0"))
MOIST_OPTIMAL_MAX = float(os.getenv("MOIST_MAX", "60.0"))

# GPIO pin numbers (BCM mode)
PIN_RELAY_PUMP      = 27
PIN_RELAY_FAN       = 22
PIN_DHT22           = 4       # board.D4 / GPIO4
MCP3008_CH_MOISTURE = 0       # SPI channel on MCP3008

# Soil moisture ADC calibration — adjust these to your sensor
DRY_VAL = 750    # ADC reading in completely dry soil
WET_VAL  = 300   # ADC reading in saturated soil

# ══════════════════════════════════════════════════════════════
#  LOGGING  — rotating file so the log doesn't fill the SD card
# ══════════════════════════════════════════════════════════════
LOG_DIR = "/var/log/technogrowth"
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    LOG_DIR = os.path.expanduser("~/technogrowth_logs")
    os.makedirs(LOG_DIR, exist_ok=True)

_file_handler = logging.handlers.RotatingFileHandler(
    f"{LOG_DIR}/sensor.log",
    maxBytes=5 * 1024 * 1024,   # 5 MB per file
    backupCount=3                # keep 3 rotated files = 15 MB max
)
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), _file_handler]
)
log = logging.getLogger("sensor_reader")

# ══════════════════════════════════════════════════════════════
#  HARDWARE INIT
# ══════════════════════════════════════════════════════════════
HARDWARE_AVAILABLE = False
dht_device = None
spi        = None
GPIO       = None   # module-level reference so cleanup can always reach it

try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
    import spidev

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # ── DHT22 — Pi 5 uses gpiochip4; use_pulseio=False is mandatory on Pi 5
    # If board.D4 raises AttributeError on Pi 5, fall back to the raw pin number.
    try:
        _dht_pin = board.D4
    except AttributeError:
        # Pi 5 compatibility: some CircuitPython builds expose GPIO4 differently
        import digitalio
        _dht_pin = board.GPIO4 if hasattr(board, "GPIO4") else board.D4

    dht_device = adafruit_dht.DHT22(_dht_pin, use_pulseio=False)
    log.info(f"DHT22 initialised on {_dht_pin}")

    # ── Relays — active-LOW, default HIGH (relay OFF = safe state)
    GPIO.setup(PIN_RELAY_PUMP, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(PIN_RELAY_FAN,  GPIO.OUT, initial=GPIO.HIGH)
    log.info(f"Relay pins set up: PUMP={PIN_RELAY_PUMP}, FAN={PIN_RELAY_FAN}")

    # ── MCP3008 via SPI
    spi = spidev.SpiDev()
    spi.open(0, 0)                   # bus 0, device 0 (CE0 = GPIO8)
    spi.max_speed_hz = 1_350_000
    log.info("SPI / MCP3008 initialised")

    HARDWARE_AVAILABLE = True
    log.info("All hardware initialised successfully.")

except (ImportError, RuntimeError, Exception) as e:
    log.warning(f"Hardware unavailable ({e}). Entering SIMULATION mode — no GPIO or sensors.")


# ══════════════════════════════════════════════════════════════
#  SAFE STATE — call whenever something goes wrong
# ══════════════════════════════════════════════════════════════
def safe_state():
    """Turn both relays OFF (HIGH = relay inactive on active-LOW board)."""
    if HARDWARE_AVAILABLE and GPIO is not None:
        try:
            GPIO.output(PIN_RELAY_PUMP, GPIO.HIGH)
            GPIO.output(PIN_RELAY_FAN,  GPIO.HIGH)
            log.info("Safe state applied: both relays OFF.")
        except Exception as e:
            log.error(f"Failed to apply safe state: {e}")


# ══════════════════════════════════════════════════════════════
#  SENSOR READING
# ══════════════════════════════════════════════════════════════

def read_temperature_humidity():
    """
    Read DHT22. Returns (temp_c, humidity_pct).
    Retries 5 times with back-off — DHT22 is notoriously flaky.
    Returns (None, None) only if all attempts fail.
    """
    if not HARDWARE_AVAILABLE:
        temp = round(28.5 + random.uniform(-1.5, 1.5), 1)
        hum  = round(65.0 + random.uniform(-5.0, 5.0), 1)
        return temp, hum

    for attempt in range(5):
        try:
            temp = dht_device.temperature
            hum  = dht_device.humidity
            if temp is not None and hum is not None:
                # Sanity-check: DHT22 range is −40 to +80°C, 0–100% RH
                if -40 <= temp <= 80 and 0 <= hum <= 100:
                    return round(temp, 1), round(hum, 1)
                else:
                    log.warning(f"DHT22 out-of-range reading: temp={temp}, hum={hum}")
        except RuntimeError as e:
            log.debug(f"DHT22 attempt {attempt + 1}/5 failed: {e}")
        time.sleep(1.0 + attempt * 0.5)   # progressive back-off: 1s, 1.5s, 2s …

    log.error("DHT22 failed after 5 attempts — returning None.")
    return None, None


def read_mcp3008(channel):
    """Read a 10-bit ADC value (0–1023) from MCP3008 via SPI."""
    if not HARDWARE_AVAILABLE or spi is None:
        return 512   # mid-scale simulation

    if not (0 <= channel <= 7):
        log.error(f"Invalid MCP3008 channel: {channel}")
        return None

    try:
        adc = spi.xfer2([1, (8 + channel) << 4, 0])
        return ((adc[1] & 3) << 8) + adc[2]
    except Exception as e:
        log.error(f"SPI read error on channel {channel}: {e}")
        return None


def read_soil_moisture():
    """
    Convert MCP3008 ADC reading to soil moisture percentage (0–100%).
    Higher ADC value = drier soil (capacitive sensor, inverted scale).
    Clamps to [0, 100] to handle out-of-calibration readings.
    """
    if not HARDWARE_AVAILABLE:
        return round(50.0 + random.uniform(-10.0, 10.0), 1)

    if DRY_VAL == WET_VAL:
        log.error("Calibration error: DRY_VAL == WET_VAL. Check constants.")
        return 0.0

    raw = read_mcp3008(MCP3008_CH_MOISTURE)
    if raw is None:
        return None

    pct = (DRY_VAL - raw) / (DRY_VAL - WET_VAL) * 100.0
    clamped = round(max(0.0, min(100.0, pct)), 1)

    if pct < 0 or pct > 100:
        log.warning(f"Moisture reading {pct:.1f}% clamped — recalibrate DRY_VAL/WET_VAL")

    return clamped


def read_npk():
    """
    Read NPK from RS-485 Modbus RTU soil sensor via USB serial adapter.
    Standard Modbus query for registers 0x0000–0x0002 (N, P, K in mg/kg).
    CRC bytes 0x05 0xCB are pre-calculated for this specific query frame.
    """
    if not HARDWARE_AVAILABLE:
        return {
            "nitrogen":   round(45.0 + random.uniform(-3.0, 3.0), 1),
            "phosphorus": round(32.0 + random.uniform(-2.0, 2.0), 1),
            "potassium":  round(28.0 + random.uniform(-2.0, 2.0), 1),
            "status": "NORMAL"
        }

    # Modbus RTU: device=0x01, func=0x03, start_reg=0x0000, count=0x0003
    QUERY = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x03, 0x05, 0xCB])

    try:
        import serial
        with serial.Serial(
            "/dev/ttyUSB0",
            baudrate=4800,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.5   # slightly longer timeout for slow RS-485 adapters
        ) as ser:
            ser.reset_input_buffer()   # flush stale bytes before querying
            ser.write(QUERY)
            time.sleep(0.3)            # RS-485 turnaround time
            response = ser.read(11)

        # Expected: 0x01 0x03 0x06 <N_H> <N_L> <P_H> <P_L> <K_H> <K_L> <CRC_L> <CRC_H>
        if len(response) < 9:
            log.warning(f"NPK short response: got {len(response)} bytes, expected 11.")
            return {"nitrogen": None, "phosphorus": None, "potassium": None, "status": "ERROR"}

        n = (response[3] << 8) | response[4]
        p = (response[5] << 8) | response[6]
        k = (response[7] << 8) | response[8]

        # Sanity check: typical soil NPK is 0–200 mg/kg
        for label, val in [("N", n), ("P", p), ("K", k)]:
            if not (0 <= val <= 2000):
                log.warning(f"NPK {label} value {val} out of expected range — check sensor wiring.")

        return {"nitrogen": n, "phosphorus": p, "potassium": k, "status": "NORMAL"}

    except Exception as e:
        log.error(f"NPK sensor error: {e}")
        return {"nitrogen": None, "phosphorus": None, "potassium": None, "status": "ERROR"}


def evaluate_npk_status(npk):
    """
    Classify NPK status based on Chinese cabbage optimal thresholds.
    Returns: 'NORMAL', 'LOW', 'HIGH', or 'ERROR'/'UNKNOWN'.
    """
    if npk.get("status") == "ERROR":
        return "ERROR"

    n = npk.get("nitrogen")
    p = npk.get("phosphorus")
    k = npk.get("potassium")

    if None in (n, p, k):
        return "UNKNOWN"

    if n < 20 or p < 15 or k < 15:
        return "LOW"
    if n > 80 or p > 60 or k > 60:
        return "HIGH"
    return "NORMAL"


# ══════════════════════════════════════════════════════════════
#  RELAY CONTROL
# ══════════════════════════════════════════════════════════════

def set_relay(pin, turn_on):
    """
    Drive a relay pin. Active-LOW board: LOW = relay ON, HIGH = relay OFF.
    Returns True on success, False on error.
    """
    if not HARDWARE_AVAILABLE or GPIO is None:
        label = "PUMP" if pin == PIN_RELAY_PUMP else "FAN"
        log.info(f"[SIM] Relay {label} → {'ON' if turn_on else 'OFF'}")
        return True

    try:
        GPIO.output(pin, GPIO.LOW if turn_on else GPIO.HIGH)
        return True
    except Exception as e:
        log.error(f"GPIO output error on pin {pin}: {e}")
        return False


def get_relay_state(pin):
    """Return 'ON' or 'OFF'. Active-LOW: LOW means ON."""
    if not HARDWARE_AVAILABLE or GPIO is None:
        return "OFF"
    try:
        return "OFF" if GPIO.input(pin) == GPIO.HIGH else "ON"
    except Exception as e:
        log.error(f"GPIO input error on pin {pin}: {e}")
        return "UNKNOWN"


# ══════════════════════════════════════════════════════════════
#  AUTO CONTROL  — threshold-based relay management
# ══════════════════════════════════════════════════════════════

def auto_control(temp, moisture):
    """
    Automatically drive relays based on sensor readings.
    Only called when auto mode is active (fetched from backend).

    Pump logic  — simple bang-bang with hysteresis:
      moisture < MIN  → pump ON
      moisture > MAX  → pump OFF (prevent waterlogging)
      in between      → leave as-is (hysteresis band)

    Fan logic:
      temp > MAX      → fan ON
      temp < MIN      → fan OFF
      in between      → leave as-is
    """
    changed = []

    if moisture is not None:
        if moisture < MOIST_OPTIMAL_MIN:
            if set_relay(PIN_RELAY_PUMP, True):
                changed.append("PUMP→ON (moisture low)")
        elif moisture > MOIST_OPTIMAL_MAX:
            if set_relay(PIN_RELAY_PUMP, False):
                changed.append("PUMP→OFF (moisture high)")
        # Hysteresis: no change if moisture is within optimal band

    if temp is not None:
        if temp > TEMP_OPTIMAL_MAX:
            if set_relay(PIN_RELAY_FAN, True):
                changed.append("FAN→ON (temp high)")
        elif temp < TEMP_OPTIMAL_MIN:
            if set_relay(PIN_RELAY_FAN, False):
                changed.append("FAN→OFF (temp low)")

    if changed:
        log.info(f"Auto-control actions: {', '.join(changed)}")


def is_auto_mode_active():
    """
    Fetch auto mode state from the backend command endpoint.
    Returns True (default) if the request fails — fail-safe to auto mode.
    """
    try:
        r = requests.get(f"{FLASK_URL}/api/devices/command", timeout=3)
        if r.ok:
            data = r.json()
            return data.get("auto_mode", True)
    except requests.RequestException:
        pass   # Network blip — assume auto mode for safety
    return True


# ══════════════════════════════════════════════════════════════
#  MANUAL COMMAND QUEUE — handles frontend toggle button presses
# ══════════════════════════════════════════════════════════════

def process_manual_commands():
    """
    Poll /api/devices/pending-commands for queued manual relay toggles.
    The Flask backend stores commands written by the frontend toggle buttons.
    Applies them here (on the Pi) then ACKs so they don't re-fire.

    Expected command format from backend:
      [{"id": "...", "device": "pump"|"fan", "state": "ON"|"OFF"}, ...]
    """
    try:
        r = requests.get(f"{FLASK_URL}/api/devices/pending-commands", timeout=3)
        if not r.ok:
            return

        commands = r.json()
        if not commands:
            return

        acked_ids = []
        for cmd in commands:
            device = cmd.get("device")
            state  = cmd.get("state")
            cmd_id = cmd.get("id")

            if device not in ("pump", "fan") or state not in ("ON", "OFF"):
                log.warning(f"Invalid command received: {cmd}")
                continue

            pin = PIN_RELAY_PUMP if device == "pump" else PIN_RELAY_FAN
            success = set_relay(pin, state == "ON")

            if success:
                log.info(f"Manual command applied: {device.upper()} → {state}")
                acked_ids.append(cmd_id)
            else:
                log.error(f"Failed to apply command: {cmd}")

        # ACK processed commands so Flask removes them from the queue
        if acked_ids:
            requests.post(
                f"{FLASK_URL}/api/devices/ack-commands",
                json={"ids": acked_ids},
                timeout=3
            )

    except requests.RequestException as e:
        log.debug(f"Command poll skipped (backend unreachable): {e}")
    except Exception as e:
        log.error(f"Command processing error: {e}", exc_info=True)


# ══════════════════════════════════════════════════════════════
#  ALERT DEDUPLICATION  — prevent flooding the database
# ══════════════════════════════════════════════════════════════

# Tracks which alert conditions are currently active.
# Key = alert condition string, Value = datetime first triggered.
_active_alert_keys = {}

def generate_alerts(temp, moisture, npk):
    """
    Return only NEW alerts — conditions that weren't already active.
    Clears resolved conditions from the active set so they can re-trigger
    if the problem comes back after being fixed.
    """
    current_conditions = {}   # key → alert dict for conditions present right now
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Temperature alerts ──
    if temp is not None:
        if temp > TEMP_OPTIMAL_MAX:
            current_conditions["temp_high"] = {
                "type": "warning", "title": "Temperature High",
                "desc": f"Temperature is {temp}°C — above optimal max of {TEMP_OPTIMAL_MAX}°C. Fan activated.",
                "sensor": "temperature", "timestamp": ts, "read": False
            }
        elif temp < TEMP_OPTIMAL_MIN:
            current_conditions["temp_low"] = {
                "type": "warning", "title": "Temperature Low",
                "desc": f"Temperature is {temp}°C — below optimal min of {TEMP_OPTIMAL_MIN}°C.",
                "sensor": "temperature", "timestamp": ts, "read": False
            }

    # ── Moisture alerts ──
    if moisture is not None:
        if moisture < MOIST_OPTIMAL_MIN:
            current_conditions["moisture_low"] = {
                "type": "warning", "title": "Soil Moisture Low",
                "desc": f"Soil moisture is {moisture}% — below optimal ({MOIST_OPTIMAL_MIN}–{MOIST_OPTIMAL_MAX}%). Pump activated.",
                "sensor": "soil_moisture", "timestamp": ts, "read": False
            }
        elif moisture > MOIST_OPTIMAL_MAX:
            current_conditions["moisture_high"] = {
                "type": "info", "title": "Soil Moisture High",
                "desc": f"Soil moisture is {moisture}% — above optimal. Check drainage.",
                "sensor": "soil_moisture", "timestamp": ts, "read": False
            }

    # ── NPK alerts ──
    if npk:
        status = npk.get("status")
        if status == "LOW":
            current_conditions["npk_low"] = {
                "type": "warning", "title": "Low NPK Levels",
                "desc": "One or more nutrients below optimal. Consider fertilisation.",
                "sensor": "npk", "timestamp": ts, "read": False
            }
        elif status == "HIGH":
            current_conditions["npk_high"] = {
                "type": "warning", "title": "High NPK Levels",
                "desc": "Nutrient levels elevated — risk of nutrient burn.",
                "sensor": "npk", "timestamp": ts, "read": False
            }
        elif status == "ERROR":
            current_conditions["npk_error"] = {
                "type": "warning", "title": "NPK Sensor Error",
                "desc": "NPK sensor returned no data. Check serial connection to /dev/ttyUSB0.",
                "sensor": "npk", "timestamp": ts, "read": False
            }

    # ── Post SUCCESS alert when all conditions clear ──
    all_clear = len(current_conditions) == 0
    was_in_alert = len(_active_alert_keys) > 0
    if all_clear and was_in_alert:
        current_conditions["all_clear"] = {
            "type": "success", "title": "Optimal Conditions Restored",
            "desc": "All sensor readings are back within optimal ranges.",
            "sensor": "system", "timestamp": ts, "read": False
        }

    # ── Filter to only NEW conditions ──
    new_alerts = []
    for key, alert in current_conditions.items():
        if key not in _active_alert_keys:
            _active_alert_keys[key] = ts
            new_alerts.append(alert)

    # ── Clear resolved conditions from active set ──
    resolved = [k for k in list(_active_alert_keys) if k not in current_conditions]
    for key in resolved:
        log.info(f"Alert condition resolved: {key}")
        del _active_alert_keys[key]

    return new_alerts


# ══════════════════════════════════════════════════════════════
#  HTTP HELPERS
# ══════════════════════════════════════════════════════════════

def post(endpoint, payload, retries=2):
    """POST JSON to Flask. Retries on transient network errors."""
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                f"{FLASK_URL}{endpoint}",
                json=payload,
                timeout=5
            )
            r.raise_for_status()
            return True
        except requests.RequestException as e:
            if attempt < retries:
                log.debug(f"POST {endpoint} attempt {attempt + 1} failed ({e}), retrying…")
                time.sleep(1)
            else:
                log.error(f"POST {endpoint} failed after {retries + 1} attempts: {e}")
    return False


# ══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════

def main():
    log.info("=" * 60)
    log.info("TechnoGrowth Sensor Reader starting")
    log.info(f"  Flask URL:     {FLASK_URL}")
    log.info(f"  Poll interval: {POLL_INTERVAL}s")
    log.info(f"  Hardware:      {'REAL' if HARDWARE_AVAILABLE else 'SIMULATION'}")
    log.info(f"  Temp range:    {TEMP_OPTIMAL_MIN}–{TEMP_OPTIMAL_MAX}°C")
    log.info(f"  Moisture range:{MOIST_OPTIMAL_MIN}–{MOIST_OPTIMAL_MAX}%")
    log.info("=" * 60)

    last_sensor_post = 0
    last_command_check = 0

    while True:
        now = time.time()

        # ── Manual command check (every COMMAND_POLL_INTERVAL seconds) ──
        if now - last_command_check >= COMMAND_POLL_INTERVAL:
            auto = is_auto_mode_active()

            # Only process manual commands when auto mode is OFF
            if not auto:
                process_manual_commands()

            last_command_check = now

        # ── Sensor read + auto control (every POLL_INTERVAL seconds) ──
        if now - last_sensor_post >= POLL_INTERVAL:
            try:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ── Read all sensors ──
                temp, humidity = read_temperature_humidity()
                moisture       = read_soil_moisture()
                npk            = read_npk()
                npk["status"]  = evaluate_npk_status(npk)

                log.info(
                    f"Temp={temp}°C | Humidity={humidity}% | "
                    f"Moisture={moisture}% | NPK={npk}"
                )

                # ── Auto relay control ──
                auto = is_auto_mode_active()
                if auto:
                    auto_control(temp, moisture)

                # ── Build and post sensor payload ──
                sensor_payload = {
                    "timestamp":     ts,
                    "temperature":   temp,
                    "humidity":      humidity,
                    "soil_moisture": moisture,
                    "npk":           npk,
                }
                post("/api/sensors", sensor_payload)

                # ── Post current device states ──
                device_payload = {
                    "timestamp":       ts,
                    "irrigation_pump": get_relay_state(PIN_RELAY_PUMP),
                    "exhaust_fan":     get_relay_state(PIN_RELAY_FAN),
                    "auto_mode":       auto,
                }
                post("/api/devices", device_payload)

                # ── Generate and post only NEW alerts ──
                alerts = generate_alerts(temp, moisture, npk)
                for alert in alerts:
                    if post("/api/alerts", alert):
                        log.warning(f"Alert: {alert['title']}")

                last_sensor_post = now

            except Exception as e:
                # ── Watchdog: catch any unhandled error, apply safe state ──
                log.error(f"Sensor loop error: {e}", exc_info=True)
                safe_state()
                # Don't update last_sensor_post so we retry immediately next tick

        # ── Sleep briefly so command checks stay responsive ──
        time.sleep(1)


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Sensor reader stopped by user (KeyboardInterrupt).")
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        # ── Clean up hardware on any exit ──
        safe_state()
        if HARDWARE_AVAILABLE and GPIO is not None:
            try:
                GPIO.cleanup()
                log.info("GPIO cleaned up.")
            except Exception as e:
                log.error(f"GPIO cleanup error: {e}")
        if spi is not None:
            try:
                spi.close()
                log.info("SPI closed.")
            except Exception as e:
                log.error(f"SPI close error: {e}")
        log.info("Sensor reader exited cleanly.")