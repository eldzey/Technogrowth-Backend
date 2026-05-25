# ══════════════════════════════════════════════════════════
#  TechnoGrowth · Chinese Cabbage — Threshold Configuration
#  Edit values here; both app.py and pi_sensor.py import this.
# ══════════════════════════════════════════════════════════

# ── Temperature (°C) ──────────────────────────────────────
TEMP_MIN      = 15.0    # below this → "Temperature Low" alert
TEMP_MAX      = 30.0    # above this → "Temperature High" alert + fan ON
TEMP_DANGER   = 31.0    # above this → "Temperature Critical" alert

# ── Soil Moisture (%) ─────────────────────────────────────
MOIST_MIN     = 40      # below this → "Soil Moisture Low" + pump ON
MOIST_MAX     = 70      # above this → "Soil Moisture High" + pump OFF
MOIST_DANGER  = 85      # below this → "Soil Moisture Critical" alert

# ── Air Humidity (%) ──────────────────────────────────────
HUMID_MIN     = 60      # below this → "Humidity Low" alert
HUMID_MAX     = 80      # above this → "Humidity High" alert
HUMID_DANGER  = 81      # below this → "Humidity Critical" alert
HUMID_FUNGAL  = 90      # above this → fan ON (fungal risk)

# ── NPK (mg/kg) ───────────────────────────────────────────
NPK_N_MIN     = 40      # nitrogen low threshold
NPK_N_MAX     = 100      # nitrogen high threshold
NPK_N_OPTIMAL = 80      # shown as optimal in analytics

NPK_P_MIN     = 25      # phosphorus low threshold
NPK_P_MAX     = 71      # phosphorus high threshold
NPK_P_OPTIMAL = 50

NPK_K_MIN     = 100      # potassium low threshold
NPK_K_MAX     = 251      # potassium high threshold
NPK_K_OPTIMAL = 200

# ── Relay auto-control ────────────────────────────────────
# Pump turns ON below MOIST_MIN, OFF when moisture reaches MOIST_MAX
# Fan turns ON above TEMP_MAX or above HUMID_FUNGAL

# ── Analytics display ranges ──────────────────────────────
# These are sent to the frontend for chart band overlays
OPTIMAL_RANGES = {
    "temp_optimal":  {"min": TEMP_MIN,  "max": TEMP_MAX},
    "moist_optimal": {"min": MOIST_MIN, "max": MOIST_MAX},
    "humid_optimal": {"min": HUMID_MIN, "max": HUMID_MAX},
    "npk_optimal":   {
        "nitrogen":   NPK_N_OPTIMAL,
        "phosphorus": NPK_P_OPTIMAL,
        "potassium":  NPK_K_OPTIMAL,
    },
}