"""
TechnoGrowth · Chinese Cabbage Monitor
Raspberry Pi sensor reader — posts to Flask every 30 s

Hardware:
  - DHT22  → GPIO 4   (temperature + humidity)
  - YL-69 / capacitive moisture sensor → MCP3008 CH0 (SPI)
  - NPK RS-485 sensor → /dev/ttyUSB0  (Modbus RTU)
  - Relay 1 → GPIO 17  (irrigation pump)
  - Relay 2 → GPIO 27  (exhaust fan)

Install deps:
  pip install adafruit-circuitpython-dht adafruit-blinka \
              minimalmodbus spidev RPi.GPIO requests

Run:
  python3 pi_sensor.py
"""

import time, requests, logging, struct
import RPi.GPIO as GPIO
import adafruit_dht
import board
import spidev
import minimalmodbus

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────
FLASK_URL      = "http://localhost:5000/api/ingest"
POLL_INTERVAL  = 30          # seconds between readings

# GPIO
PUMP_PIN       = 17          # Relay: irrigation pump (active LOW)
FAN_PIN        = 27          # Relay: exhaust fan     (active LOW)

# Thresholds (auto mode)
TEMP_MAX       = 30.0        # °C  — fan ON above this
MOIST_MIN      = 43          # %   — pump ON below this
MOIST_MAX      = 60          # %   — pump OFF above this
HUMID_MAX      = 88          # %   — fan ON above this (fungal risk)
HUMID_MIN      = 65          # %   — alert below this

# Growth stages (days since transplant)
STAGES = [
    (0,  7,  "Seedling"),
    (8,  20, "Vegetative"),
    (21, 40, "Head Formation"),
    (41, 60, "Maturation"),
]

# NPK RS-485
NPK_PORT       = "/dev/ttyUSB0"
NPK_BAUDRATE   = 4800
NPK_ADDR       = 1           # Modbus slave address

# MCP3008 SPI (soil moisture ADC)
SPI_BUS        = 0
SPI_DEVICE     = 0
SPI_SPEED      = 1_350_000
MOISTURE_CH    = 0           # MCP3008 channel

# ── GPIO Setup ───────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PUMP_PIN, GPIO.OUT, initial=GPIO.HIGH)   # HIGH = relay OFF
GPIO.setup(FAN_PIN,  GPIO.OUT, initial=GPIO.HIGH)

# ── DHT22 ────────────────────────────────────────────────
dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

def read_dht22():
    """Return (temperature_c, humidity_pct) or (None, None) on error."""
    for _ in range(3):
        try:
            t = dht.temperature
            h = dht.humidity
            if t is not None and h is not None:
                return round(float(t), 1), round(float(h), 1)
        except RuntimeError as e:
            log.warning("DHT22 read error: %s", e)
            time.sleep(2)
    return None, None

# ── MCP3008 SPI (soil moisture) ──────────────────────────
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = SPI_SPEED

def read_mcp3008(channel: int) -> int:
    """Read 10-bit ADC value (0-1023) from MCP3008."""
    assert 0 <= channel <= 7
    r = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((r[1] & 3) << 8) | r[2]

def read_soil_moisture() -> int:
    """Convert ADC reading to moisture percentage (0-100%)."""
    raw = read_mcp3008(MOISTURE_CH)
    # Calibrate: 0 = dry (ADC ~900), 100 = wet (ADC ~100)
    DRY, WET = 900, 100
    pct = (DRY - raw) / (DRY - WET) * 100
    return max(0, min(100, round(pct)))

# ── NPK Sensor (RS-485 Modbus RTU) ──────────────────────
try:
    npk_instrument = minimalmodbus.Instrument(NPK_PORT, NPK_ADDR)
    npk_instrument.serial.baudrate = NPK_BAUDRATE
    npk_instrument.serial.bytesize = 8
    npk_instrument.serial.parity   = "N"
    npk_instrument.serial.stopbits = 1
    npk_instrument.serial.timeout  = 1
    npk_instrument.mode = minimalmodbus.MODE_RTU
    NPK_AVAILABLE = True
except Exception as e:
    log.warning("NPK sensor unavailable: %s", e)
    NPK_AVAILABLE = False

def read_npk() -> dict:
    """
    Read N, P, K from RS-485 sensor (registers 0x001E–0x0020).
    Returns dict with nitrogen, phosphorus, potassium (mg/kg) and status.
    """
    if not NPK_AVAILABLE:
        return {"nitrogen": None, "phosphorus": None, "potassium": None, "status": "UNAVAILABLE"}
    try:
        n = npk_instrument.read_register(0x001E, functioncode=3)
        p = npk_instrument.read_register(0x001F, functioncode=3)
        k = npk_instrument.read_register(0x0020, functioncode=3)
        status = classify_npk(n, p, k)
        return {"nitrogen": n, "phosphorus": p, "potassium": k, "status": status}
    except Exception as e:
        log.warning("NPK read error: %s", e)
        return {"nitrogen": None, "phosphorus": None, "potassium": None, "status": "ERROR"}

def classify_npk(n, p, k) -> str:
    """Simple threshold classification for Chinese cabbage."""
    LOW_N, LOW_P, LOW_K   = 30, 20, 18
    HIGH_N, HIGH_P, HIGH_K = 70, 50, 50
    issues = []
    if n < LOW_N:   issues.append("N-LOW")
    elif n > HIGH_N: issues.append("N-HIGH")
    if p < LOW_P:   issues.append("P-LOW")
    elif p > HIGH_P: issues.append("P-HIGH")
    if k < LOW_K:   issues.append("K-LOW")
    elif k > HIGH_K: issues.append("K-HIGH")
    return "NORMAL" if not issues else ",".join(issues)

# ── Growth stage ─────────────────────────────────────────
_transplant_day = 21   # update to actual day-since-transplant counter

def current_stage() -> str:
    for start, end, label in STAGES:
        if start <= _transplant_day <= end:
            return label
    return "Post-Harvest"

# ── Auto relay control ───────────────────────────────────
_pump_on = False
_fan_on  = False

def update_relays(temp, moist, humid):
    global _pump_on, _fan_on

    # Irrigation pump: ON when moisture too low, OFF when restored
    if moist is not None:
        if moist < MOIST_MIN and not _pump_on:
            GPIO.output(PUMP_PIN, GPIO.LOW)   # relay ON
            _pump_on = True
            log.info("Pump ON — moisture %s%%", moist)
        elif moist >= MOIST_MAX and _pump_on:
            GPIO.output(PUMP_PIN, GPIO.HIGH)  # relay OFF
            _pump_on = False
            log.info("Pump OFF — moisture %s%%", moist)

    # Exhaust fan: ON when temp too high OR humidity too high
    fan_needed = (
        (temp  is not None and temp  > TEMP_MAX)  or
        (humid is not None and humid > HUMID_MAX)
    )
    if fan_needed and not _fan_on:
        GPIO.output(FAN_PIN, GPIO.LOW)
        _fan_on = True
        log.info("Fan ON — temp=%s°C humid=%s%%", temp, humid)
    elif not fan_needed and _fan_on:
        GPIO.output(FAN_PIN, GPIO.HIGH)
        _fan_on = False
        log.info("Fan OFF")

def relay_state(pin_on: bool) -> str:
    return "ON" if pin_on else "OFF"

# ── Post to Flask ────────────────────────────────────────
def post_reading(temp, humid, moist, npk):
    payload = {
        "temperature":    temp,
        "humidity":       humid,
        "soil_moisture":  moist,
        "npk":            npk,
        "stage":          current_stage(),
        "irrigation_pump": relay_state(_pump_on),
        "exhaust_fan":     relay_state(_fan_on),
        "auto_mode":       True,
    }
    try:
        resp = requests.post(FLASK_URL, json=payload, timeout=5)
        resp.raise_for_status()
        log.info("Posted: temp=%.1f°C humid=%.1f%% moist=%d%% npk=%s",
                 temp or 0, humid or 0, moist or 0, npk.get("status"))
    except requests.RequestException as e:
        log.error("Post failed: %s", e)

# ── Main loop ────────────────────────────────────────────
def main():
    log.info("Chinese Cabbage Monitor — sensor loop starting (interval %ds)", POLL_INTERVAL)
    try:
        while True:
            temp,  humid = read_dht22()
            moist        = read_soil_moisture()
            npk          = read_npk()

            update_relays(temp, moist, humid)
            post_reading(temp, humid, moist, npk)

            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    finally:
        GPIO.output(PUMP_PIN, GPIO.HIGH)   # safety: relays off
        GPIO.output(FAN_PIN,  GPIO.HIGH)
        GPIO.cleanup()
        spi.close()
        dht.exit()

if __name__ == "__main__":
    main()