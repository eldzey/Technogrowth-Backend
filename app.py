# ══════════════════════════════════════════════════════
#  TechnoGrowth · Flask Backend (app.py)
#  Matches the front-end design by Lyka Jane Hidalgo
#
#  HOW TO RUN:
#    1. pip install flask
#    2. python app.py
#    3. Open browser: http://127.0.0.1:5000
# ══════════════════════════════════════════════════════

from flask import Flask, render_template, jsonify
import random
from datetime import datetime

app = Flask(__name__)

# ──────────────────────────────────────────
#  MOCK SENSOR FUNCTIONS
#  Replace these with real sensor reads later
# ──────────────────────────────────────────

def read_temperature():
    # LATER: Use Adafruit_DHT to read from DHT22
    return round(29 + random.uniform(-1.5, 1.5), 1)

def read_humidity():
    # LATER: Use Adafruit_DHT to read from DHT22
    return round(55 + random.uniform(-5, 8), 1)

def read_soil_moisture():
    # LATER: Read from capacitive moisture sensor via ADC
    return round(42 + random.uniform(-3, 3), 1)

def read_npk():
    # LATER: Read from NPK sensor via RS485 serial
    return {"nitrogen": 45, "phosphorus": 32, "potassium": 28, "status": "NORMAL"}

def get_growth_data():
    return {
        "day":          27,
        "harvest_day":  30,
        "days_left":    3,
        "stage":        "Late Vegetative",
        "health":       "Healthy",
        "growth_score": 88,
        "leaf_count":   12,
        "size_cm":      35,
        "growth_rate":  1.3,
    }

def get_device_status():
    return {
        "irrigation_pump": {"status": "OFF", "last_run": "2 hours ago", "total_today": "3.5 hrs"},
        "exhaust_fan":     {"status": "OFF", "last_run": "3 hours ago", "total_today": "1.2 hrs"},
        "humidifier":      {"status": "OFF", "last_run": "Never",       "total_today": "0 hrs"},
        "auto_mode":       True
    }

def get_alerts():
    return [
        {"type": "warning", "title": "Soil Moisture Low",          "desc": "Soil moisture has dropped to 42%. Consider irrigation.", "time": "2 hours ago"},
        {"type": "info",    "title": "Growth Milestone",           "desc": "Your Chinese cabbage has reached 12 leaves!",             "time": "5 hours ago"},
        {"type": "warning", "title": "Temperature Rising",         "desc": "Temperature increased to 29°C. Monitor closely.",         "time": "1 day ago"},
        {"type": "info",    "title": "Auto Irrigation Completed",  "desc": "Irrigation pump ran for 2 hours as scheduled.",           "time": "2 hours ago"},
        {"type": "success", "title": "Optimal Conditions Achieved","desc": "All environmental parameters are within ideal ranges.",    "time": "1 day ago"},
        {"type": "info",    "title": "Humidity Suggestion",        "desc": "Consider increasing humidity slightly for optimal growth.","time": "2 days ago"},
    ]

# ──────────────────────────────────────────
#  ROUTES
# ──────────────────────────────────────────

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/sensors')
def api_sensors():
    return jsonify({
        "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temperature":   read_temperature(),
        "humidity":      read_humidity(),
        "soil_moisture": read_soil_moisture(),
        "npk":           read_npk(),
    })

@app.route('/api/growth')
def api_growth():
    return jsonify(get_growth_data())

@app.route('/api/devices')
def api_devices():
    return jsonify(get_device_status())

@app.route('/api/alerts')
def api_alerts():
    return jsonify(get_alerts())

@app.route('/api/status')
def api_status():
    return jsonify({"status": "online", "version": "2.0.0"})

# ──────────────────────────────────────────
#  RUN
# ──────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("  TechnoGrowth · Chinese Cabbage Monitor")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
