# ══════════════════════════════════════════════════════════
#  TechnoGrowth · Chinese Cabbage — Threshold Configuration
#  Edit values here; both app.py and pi_sensor.py import this.
# ══════════════════════════════════════════════════════════

# ── Temperature (°C) ──────────────────────────────────────
TEMP_MIN      = 25.0    # below this → "Temperature Low" alert
TEMP_MAX      = 30.0    # above this → "Temperature High" alert + fan ON
TEMP_DANGER   = 35.0    # above this → "Temperature Critical" alert

# ── Soil Moisture (%) ─────────────────────────────────────
MOIST_MIN     = 43      # below this → "Soil Moisture Low" + pump ON
MOIST_MAX     = 60      # above this → "Soil Moisture High" + pump OFF
MOIST_DANGER  = 35      # below this → "Soil Moisture Critical" alert

# ── Air Humidity (%) ──────────────────────────────────────
HUMID_MIN     = 70      # below this → "Humidity Low" alert
HUMID_MAX     = 85      # above this → "Humidity High" alert
HUMID_DANGER  = 60      # below this → "Humidity Critical" alert
HUMID_FUNGAL  = 90      # above this → fan ON (fungal risk)

# ── NPK (mg/kg) ───────────────────────────────────────────
NPK_N_MIN     = 30      # nitrogen low threshold
NPK_N_MAX     = 70      # nitrogen high threshold
NPK_N_OPTIMAL = 50      # shown as optimal in analytics

NPK_P_MIN     = 20      # phosphorus low threshold
NPK_P_MAX     = 50      # phosphorus high threshold
NPK_P_OPTIMAL = 35

NPK_K_MIN     = 18      # potassium low threshold
NPK_K_MAX     = 50      # potassium high threshold
NPK_K_OPTIMAL = 30

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