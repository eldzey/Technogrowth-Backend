from flask import Flask, request, jsonify, render_template, Response, send_file
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime, timedelta

import csv
import io
import os
import logging

from thresholds import (
    TEMP_MIN, TEMP_MAX, TEMP_DANGER,
    MOIST_MIN, MOIST_MAX, MOIST_DANGER,
    HUMID_MIN, HUMID_MAX, HUMID_DANGER, HUMID_FUNGAL,
    NPK_N_MIN, NPK_N_MAX, NPK_P_MIN, NPK_P_MAX, NPK_K_MIN, NPK_K_MAX,
    OPTIMAL_RANGES,
)

# ── LOAD ENVIRONMENT ──────────────────────────────────────
load_dotenv()

# ── FLASK APP ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── LOGGING ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("technogrowth")

# ── MONGODB ───────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client    = MongoClient(MONGO_URI)
db        = client["Technogrowth"]        # ✅ correct database name

sensors_col        = db["sensor_logs"]    # ✅ correct collection name
alerts_col         = db["alerts"]
devices_col        = db["devices"]
npk_trends_col     = db["npk_trends"]
ai_predictions_col = db["ai_predictions"]

log.info(f"Connected to MongoDB: {MONGO_URI}")

# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def serialize(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc


def days_filter(days_str):
    try:
        days  = int(days_str)
        since = datetime.utcnow() - timedelta(days=days)
        return {"timestamp": {"$gte": since}}
    except (TypeError, ValueError):
        return {}


# ══════════════════════════════════════════════════════════
#  FIELD NAME MAPPER
#  MongoDB stores: temp, hum, moisture_avg
#  App/frontend expects: temperature, humidity, soil_moisture
# ══════════════════════════════════════════════════════════

def normalize_sensor(doc):
    """Map MongoDB field names to standard field names used by the frontend."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

    # ✅ Map actual field names → frontend field names
    doc["temperature"]   = doc.pop("temp",         doc.get("temperature"))
    doc["humidity"]      = doc.pop("hum",          doc.get("humidity"))
    doc["soil_moisture"] = doc.pop("moisture_avg", doc.get("soil_moisture"))

    # Build npk sub-object if stored flat
    if "npk" not in doc or not doc["npk"]:
        doc["npk"] = {
            "nitrogen":   doc.get("nitrogen"),
            "phosphorus": doc.get("phosphorus"),
            "potassium":  doc.get("potassium"),
            "status":     doc.get("npk_status", "NORMAL"),
        }
    return doc


# ══════════════════════════════════════════════════════════
#  FRONTEND
# ══════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    return render_template("index.html")


# ══════════════════════════════════════════════════════════
#  SENSORS
# ══════════════════════════════════════════════════════════

@app.route("/api/sensors/latest")
def sensors_latest():
    # Try timestamp sort first, fall back to _id (insertion order)
    doc = sensors_col.find_one(sort=[("timestamp", DESCENDING)])
    if not doc or "timestamp" not in doc:
        doc = sensors_col.find_one(sort=[("_id", DESCENDING)])
    if not doc:
        return jsonify({}), 404
    return jsonify(normalize_sensor(doc))


@app.route("/api/sensors")
def sensors_list():
    limit = min(int(request.args.get("limit", 50)), 200)
    skip  = int(request.args.get("skip", 0))
    filt  = days_filter(request.args.get("days"))
    docs  = list(sensors_col.find(filt, sort=[("timestamp", DESCENDING)]).skip(skip).limit(limit))
    total = sensors_col.count_documents(filt)
    return jsonify({"records": [normalize_sensor(d) for d in docs], "count": total})


# ══════════════════════════════════════════════════════════
#  HISTORY — daily averages for charts
# ══════════════════════════════════════════════════════════

@app.route("/api/history")
def history():
    since = datetime.utcnow() - timedelta(days=7)

    # Check if documents have timestamps before filtering
    has_timestamps = sensors_col.find_one({"timestamp": {"$exists": True}}) is not None

    if has_timestamps:
        docs = list(sensors_col.find(
            {"timestamp": {"$gte": since}},
            sort=[("timestamp", ASCENDING)]
        ))
    else:
        # No timestamps — fetch last 200 records by insertion order
        docs = list(sensors_col.find({}, sort=[("_id", ASCENDING)]).limit(200))

    buckets = {}
    counter = 0
    for d in docs:
        ts = d.get("timestamp")
        if isinstance(ts, datetime):
            label = ts.strftime("%m-%d")
        else:
            # No timestamp: group every 28 docs into a bucket (simulate daily avg)
            label = f"#{counter // 28 + 1}"
        counter += 1
        buckets.setdefault(label, {"temp": [], "moist": [], "humid": []})

        # ✅ Read using actual MongoDB field names
        if d.get("temp")         is not None: buckets[label]["temp"].append(d["temp"])
        if d.get("moisture_avg") is not None: buckets[label]["moist"].append(d["moisture_avg"])
        if d.get("hum")          is not None: buckets[label]["humid"].append(d["hum"])

    labels, temps, moists, humids = [], [], [], []
    for label in sorted(buckets.keys()):
        vals = buckets[label]
        labels.append(label)
        temps.append( round(sum(vals["temp"])  / len(vals["temp"]),  1) if vals["temp"]  else None)
        moists.append(round(sum(vals["moist"]) / len(vals["moist"]), 1) if vals["moist"] else None)
        humids.append(round(sum(vals["humid"]) / len(vals["humid"]), 1) if vals["humid"] else None)

    if not labels:
        labels = ["Day 21", "Day 22", "Day 23", "Day 24", "Day 25", "Day 26", "Day 27"]
        temps  = [28.1, 28.6, 29.0, 28.8, 29.4, 29.1, 29.0]
        moists = [54,   51,   48,   45,   40,   43,   42  ]
        humids = [78,   76,   80,   82,   79,   75,   77  ]

    return jsonify({
        "labels":        labels,
        "temperature":   temps,
        "soil_moisture": moists,
        "humidity":      humids,
        **OPTIMAL_RANGES,
    })


# ══════════════════════════════════════════════════════════
#  NPK TREND
# ══════════════════════════════════════════════════════════

@app.route("/api/npk-trend")
def npk_trend():
    since  = datetime.utcnow() - timedelta(days=7)

    # Check if documents have timestamps before filtering
    has_timestamps = sensors_col.find_one({"timestamp": {"$exists": True}}) is not None

    if has_timestamps:
        docs = list(sensors_col.find(
            {"timestamp": {"$gte": since}},
            sort=[("timestamp", ASCENDING)]
        ))
    else:
        docs = list(sensors_col.find({}, sort=[("_id", ASCENDING)]).limit(200))

    latest = sensors_col.find_one(sort=[("_id", DESCENDING)])

    labels, ns, ps, ks = [], [], [], []
    counter = 0
    for d in docs:
        ts = d.get("timestamp")
        if isinstance(ts, datetime):
            labels.append(ts.strftime("%m-%d"))
        else:
            labels.append(f"#{counter // 28 + 1}")
        counter += 1
        ns.append(d.get("nitrogen"))
        ps.append(d.get("phosphorus"))
        ks.append(d.get("potassium"))

    if not labels:
        labels = ["Day 21", "Day 22", "Day 23", "Day 24", "Day 25", "Day 26", "Day 27"]
        ns = [42, 43, 44, 44, 45, 45, 45]
        ps = [30, 31, 31, 32, 32, 32, 32]
        ks = [26, 26, 27, 27, 28, 28, 28]

    current = {
        "nitrogen":   latest.get("nitrogen")   if latest else 45,
        "phosphorus": latest.get("phosphorus") if latest else 32,
        "potassium":  latest.get("potassium")  if latest else 28,
        "status":     latest.get("npk_status", "NORMAL") if latest else "NORMAL",
    }

    return jsonify({
        "labels":     labels,
        "nitrogen":   ns,
        "phosphorus": ps,
        "potassium":  ks,
        "current":    current,
        "optimal":    OPTIMAL_RANGES["npk_optimal"],
    })


# ══════════════════════════════════════════════════════════
#  DEVICES
# ══════════════════════════════════════════════════════════

@app.route("/api/devices/latest")
def devices_latest():
    doc = devices_col.find_one(sort=[("timestamp", DESCENDING)])
    if not doc:
        return jsonify({
            "irrigation_pump": "OFF",
            "exhaust_fan":     "OFF",
            "humidifier":      "OFF",
            "auto_mode":       True,
            "timestamp":       "—"
        })
    return jsonify(serialize(doc))


# ══════════════════════════════════════════════════════════
#  ALERTS
# ══════════════════════════════════════════════════════════

@app.route("/api/alerts")
def alerts_list():
    limit = min(int(request.args.get("limit", 50)), 200)
    filt  = days_filter(request.args.get("days"))
    docs  = list(alerts_col.find(filt, sort=[("timestamp", DESCENDING)]).limit(limit))
    total = alerts_col.count_documents(filt)
    return jsonify({"records": [serialize(d) for d in docs], "count": total})


@app.route("/api/alerts/unread-count")
def alerts_unread():
    count = alerts_col.count_documents({"read": False})
    return jsonify({"count": count})


@app.route("/api/alerts/<alert_id>/read", methods=["PATCH"])
def mark_alert_read(alert_id):
    alerts_col.update_one({"_id": ObjectId(alert_id)}, {"$set": {"read": True}})
    return jsonify({"ok": True})


@app.route("/api/alerts/mark-all-read", methods=["POST", "PATCH"])
def mark_all_read():
    alerts_col.update_many({"read": False}, {"$set": {"read": True}})
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════
#  HISTORY LOG — multi-collection
# ══════════════════════════════════════════════════════════

@app.route("/api/logs")
def logs():
    col_name = request.args.get("collection", "sensors")
    limit    = min(int(request.args.get("limit", 50)), 200)
    skip     = int(request.args.get("skip", 0))
    filt     = days_filter(request.args.get("days"))

    col_map = {
        "sensors":    sensors_col,
        "alerts":     alerts_col,
        "devices":    devices_col,
        "npk_trends": npk_trends_col,
    }
    col = col_map.get(col_name, sensors_col)

    # Check if this collection actually has timestamp fields
    # If not, skip the days filter entirely and query by _id instead
    has_timestamps = col.find_one({"timestamp": {"$exists": True}}) is not None

    if has_timestamps and filt:
        docs  = list(col.find(filt, sort=[("timestamp", DESCENDING)]).skip(skip).limit(limit))
        total = col.count_documents(filt)
    else:
        # No timestamps — fetch all records sorted by insertion order
        docs  = list(col.find({}, sort=[("_id", DESCENDING)]).skip(skip).limit(limit))
        total = col.count_documents({})

    # Normalize sensor docs so frontend gets standard field names
    if col_name == "sensors":
        records = [normalize_sensor(d) for d in docs]
    else:
        records = [serialize(d) for d in docs]

    return jsonify({"records": records, "count": total})


# ══════════════════════════════════════════════════════════
#  INGEST — Raspberry Pi POSTs data here
# ══════════════════════════════════════════════════════════

@app.route("/api/ingest", methods=["POST"])
def ingest():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "No JSON received"}), 400

    now = datetime.utcnow()

    # ✅ Store using actual MongoDB field names
    sensor_doc = {
        "timestamp":   now,
        "temp":        payload.get("temperature", payload.get("temp")),
        "hum":         payload.get("humidity",    payload.get("hum")),
        "moisture_avg":payload.get("soil_moisture", payload.get("moisture_avg")),
        "nitrogen":    payload.get("npk", {}).get("nitrogen",   payload.get("nitrogen")),
        "phosphorus":  payload.get("npk", {}).get("phosphorus", payload.get("phosphorus")),
        "potassium":   payload.get("npk", {}).get("potassium",  payload.get("potassium")),
        "npk_status":  payload.get("npk", {}).get("status",     payload.get("npk_status", "NORMAL")),
        "image":       payload.get("image", "latest_cabbage.jpg"),
        "stage":       payload.get("stage"),
    }
    sensors_col.insert_one(sensor_doc)

    device_doc = {
        "timestamp":       now,
        "irrigation_pump": payload.get("irrigation_pump", "OFF"),
        "exhaust_fan":     payload.get("exhaust_fan", "OFF"),
        "humidifier":      payload.get("humidifier", "OFF"),
        "auto_mode":       payload.get("auto_mode", True),
    }
    devices_col.insert_one(device_doc)

    _auto_alert(now, payload)

    log.info(f"Ingest OK — temp={sensor_doc['temp']} moisture={sensor_doc['moisture_avg']} hum={sensor_doc['hum']}")
    return jsonify({"ok": True, "timestamp": now.isoformat()}), 201


def _auto_alert(now, payload):
    """Insert threshold alerts using values from thresholds.py."""
    def push(atype, title, desc):
        if not alerts_col.find_one({"title": title, "read": False}):
            alerts_col.insert_one({
                "timestamp": now,
                "type":      atype,
                "title":     title,
                "desc":      desc,
                "read":      False
            })

    # ✅ Accept both naming conventions from Pi
    t   = payload.get("temperature",  payload.get("temp"))
    m   = payload.get("soil_moisture", payload.get("moisture_avg"))
    h   = payload.get("humidity",     payload.get("hum"))
    npk = payload.get("npk", {})

    # ── Temperature
    if t is not None:
        if t >= TEMP_DANGER:
            push("warning", "Temperature Critical", f"Temperature is {t}°C — critically high (limit: {TEMP_DANGER}°C).")
        elif t > TEMP_MAX:
            push("warning", "Temperature High",     f"Temperature is {t}°C — above safe limit of {TEMP_MAX}°C.")
        elif t < TEMP_MIN:
            push("warning", "Temperature Low",      f"Temperature is {t}°C — below optimal range of {TEMP_MIN}°C.")

    # ── Soil Moisture
    if m is not None:
        if m < MOIST_DANGER:
            push("warning", "Soil Moisture Critical", f"Soil moisture is {m}% — critically low (threshold: {MOIST_DANGER}%). Irrigate immediately.")
        elif m < MOIST_MIN:
            push("warning", "Soil Moisture Low",      f"Soil moisture is {m}% — below optimal {MOIST_MIN}%.")
        elif m > MOIST_MAX:
            push("warning", "Soil Moisture High",     f"Soil moisture is {m}% — above optimal {MOIST_MAX}%.")

    # ── Humidity
    if h is not None:
        if h < HUMID_DANGER:
            push("warning", "Humidity Critical",  f"Humidity is {h}% — critically low (threshold: {HUMID_DANGER}%). Risk of wilting.")
        elif h < HUMID_MIN:
            push("warning", "Humidity Low",       f"Humidity is {h}% — below optimal {HUMID_MIN}%.")
        elif h > HUMID_FUNGAL:
            push("warning", "Humidity High",      f"Humidity is {h}% — above {HUMID_FUNGAL}%. Fungal disease risk.")
        elif h > HUMID_MAX:
            push("warning", "Humidity Elevated",  f"Humidity is {h}% — above optimal {HUMID_MAX}%.")

    # ── NPK
    npk_status = npk.get("status") or payload.get("npk_status")
    if npk_status and npk_status != "NORMAL":
        push("warning", "NPK Imbalance", f"NPK sensor reports: {npk_status}. Check nutrient levels.")


# ══════════════════════════════════════════════════════════
#  AI PREDICTIONS
# ══════════════════════════════════════════════════════════

@app.route("/api/ai/predict", methods=["POST"])
def ai_predict():
    """Receives AI predictions from React/HTML frontend."""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No data received"}), 400

    prediction = data.get("prediction")
    confidence = data.get("confidence")

    ai_doc = {
        "timestamp":  datetime.utcnow(),
        "prediction": prediction,
        "confidence": confidence,
    }
    ai_predictions_col.insert_one(ai_doc)
    log.info(f"AI Prediction: {prediction} ({confidence}%)")

    return jsonify({"ok": True, "message": "AI prediction saved successfully"})


@app.route("/api/ai/history")
def ai_history():
    docs = list(
        ai_predictions_col.find(
            {},
            sort=[("timestamp", DESCENDING)]
        ).limit(50)
    )
    return jsonify({"records": [serialize(d) for d in docs]})


# ══════════════════════════════════════════════════════════
#  THRESHOLDS API
# ══════════════════════════════════════════════════════════

@app.route("/api/thresholds")
def get_thresholds():
    """Returns all configured threshold values."""
    return jsonify({
        "temperature":   {"min": TEMP_MIN,  "max": TEMP_MAX,  "danger": TEMP_DANGER},
        "soil_moisture": {"min": MOIST_MIN, "max": MOIST_MAX, "danger": MOIST_DANGER},
        "humidity":      {"min": HUMID_MIN, "max": HUMID_MAX, "danger": HUMID_DANGER, "fungal": HUMID_FUNGAL},
        "npk": {
            "nitrogen":   {"min": NPK_N_MIN, "max": NPK_N_MAX, "optimal": OPTIMAL_RANGES["npk_optimal"]["nitrogen"]},
            "phosphorus": {"min": NPK_P_MIN, "max": NPK_P_MAX, "optimal": OPTIMAL_RANGES["npk_optimal"]["phosphorus"]},
            "potassium":  {"min": NPK_K_MIN, "max": NPK_K_MAX, "optimal": OPTIMAL_RANGES["npk_optimal"]["potassium"]},
        }
    })


# ══════════════════════════════════════════════════════════
#  EXPORT CSV
# ══════════════════════════════════════════════════════════

@app.route("/export/csv")
def export_csv():
    since = datetime.utcnow() - timedelta(days=30)
    docs  = list(sensors_col.find(
        {"timestamp": {"$gte": since}},
        sort=[("timestamp", DESCENDING)]
    ).limit(500))

    buf    = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Timestamp", "Temperature (°C)", "Soil Moisture (%)",
        "Humidity (%)", "Nitrogen", "Phosphorus", "Potassium", "NPK Status", "Stage"
    ])
    for d in docs:
        ts = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(d.get("timestamp"), datetime) else ""
        writer.writerow([
            ts,
            d.get("temp",         ""),   # ✅ actual field name
            d.get("moisture_avg", ""),   # ✅ actual field name
            d.get("hum",          ""),   # ✅ actual field name
            d.get("nitrogen",     ""),
            d.get("phosphorus",   ""),
            d.get("potassium",    ""),
            d.get("npk_status",   ""),
            d.get("stage",        ""),
        ])

    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"cabbage_sensor_data_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    )


# ══════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════

@app.route("/api/health")
def health():
    sensor_count = sensors_col.count_documents({})
    latest       = sensors_col.find_one(sort=[("timestamp", DESCENDING)])
    last_reading = latest["timestamp"].isoformat() if latest and isinstance(latest.get("timestamp"), datetime) else None
    return jsonify({
        "status":       "ok",
        "time":         datetime.utcnow().isoformat(),
        "sensor_count": sensor_count,
        "last_reading": last_reading,
    })


# ══════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("  TechnoGrowth · Chinese Cabbage Monitor")
    print("  http://127.0.0.1:5000")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=True)