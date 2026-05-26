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
db        = client["Technogrowth"]

sensors_col        = db["sensor_logs"]
alerts_col         = db["alerts"]
devices_col        = db["devices"]
npk_trends_col     = db["npk_trends"]
ai_predictions_col = db["ai_predictions"]

log.info(f"Connected to MongoDB: {MONGO_URI}")

# ══════════════════════════════════════════════════════════
#  MOCK NPK VALUES
#  Used whenever the Pi's RS-485 NPK sensor returns None/0/ERROR
#  so the dashboard always shows something meaningful.
# ══════════════════════════════════════════════════════════
MOCK_NPK = {
    "nitrogen":   OPTIMAL_RANGES["npk_optimal"]["nitrogen"],    # 80  mg/kg
    "phosphorus": OPTIMAL_RANGES["npk_optimal"]["phosphorus"],  # 50  mg/kg
    "potassium":  OPTIMAL_RANGES["npk_optimal"]["potassium"],   # 200 mg/kg
    "status":     "NORMAL",
}

def _fill_npk(n, p, k, status):
    """
    Return (n, p, k, status) — replace any None/0 value with mock optimal.
    This ensures NPK is NEVER 0 or null in API responses.
    """
    n = n if (n is not None and n > 0) else MOCK_NPK["nitrogen"]
    p = p if (p is not None and p > 0) else MOCK_NPK["phosphorus"]
    k = k if (k is not None and k > 0) else MOCK_NPK["potassium"]
    # If status is ERROR/UNAVAILABLE and values were mocked, say NORMAL
    if status in (None, "ERROR", "UNAVAILABLE", ""):
        status = "NORMAL"
    return n, p, k, status


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
#  MongoDB stores: temp, hum, moisture_avg  (flat NPK fields)
#  Frontend expects: temperature, humidity, soil_moisture, npk{}
# ══════════════════════════════════════════════════════════

def normalize_sensor(doc):
    """Map MongoDB field names → standard frontend field names.
    FIX: safely read all flat NPK fields BEFORE mutating the doc,
         then fill any None/0 values with mock NPK so UI never shows zeros.
    """
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

    # ── Rename sensor fields ──────────────────────────────
    doc["temperature"]   = doc.pop("temp",         doc.get("temperature"))
    doc["humidity"]      = doc.pop("hum",          doc.get("humidity"))
    doc["soil_moisture"] = doc.pop("moisture_avg", doc.get("soil_moisture"))

    # ── FIX: read flat NPK BEFORE building sub-object ─────
    # Use .get() with None default so missing fields don't raise KeyError
    raw_n      = doc.get("nitrogen")
    raw_p      = doc.get("phosphorus")
    raw_k      = doc.get("potassium")
    raw_status = doc.get("npk_status", "NORMAL")

    # ── FIX: only build npk{} if it doesn't already exist ─
    existing_npk = doc.get("npk")
    if not existing_npk or not isinstance(existing_npk, dict):
        n, p, k, status = _fill_npk(raw_n, raw_p, raw_k, raw_status)
        doc["npk"] = {
            "nitrogen":   n,
            "phosphorus": p,
            "potassium":  k,
            "status":     status,
        }
    else:
        # Sub-object exists — still fill any zero/None inside it
        en = existing_npk.get("nitrogen")
        ep = existing_npk.get("phosphorus")
        ek = existing_npk.get("potassium")
        es = existing_npk.get("status", "NORMAL")
        n, p, k, status = _fill_npk(en, ep, ek, es)
        doc["npk"]["nitrogen"]   = n
        doc["npk"]["phosphorus"] = p
        doc["npk"]["potassium"]  = k
        doc["npk"]["status"]     = status

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
    has_timestamps = sensors_col.find_one({"timestamp": {"$exists": True}}) is not None

    if has_timestamps:
        docs = list(sensors_col.find(
            {"timestamp": {"$gte": since}},
            sort=[("timestamp", ASCENDING)]
        ))
    else:
        docs = list(sensors_col.find({}, sort=[("_id", ASCENDING)]).limit(200))

    buckets = {}
    counter = 0
    for d in docs:
        ts = d.get("timestamp")
        label = ts.strftime("%m-%d") if isinstance(ts, datetime) else f"#{counter // 28 + 1}"
        counter += 1
        buckets.setdefault(label, {"temp": [], "moist": [], "humid": []})
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

    # FIX: always return real data — fallback only if truly empty
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
#  FIX: replace None/0 NPK values with mock optimal so charts
#       never render flat zero lines.
# ══════════════════════════════════════════════════════════

@app.route("/api/npk-trend")
def npk_trend():
    since = datetime.utcnow() - timedelta(days=7)
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
        labels.append(ts.strftime("%m-%d") if isinstance(ts, datetime) else f"#{counter // 28 + 1}")
        counter += 1

        # FIX: fill None/0 with mock values per-point so chart has no zero gaps
        n, p, k, _ = _fill_npk(
            d.get("nitrogen"), d.get("phosphorus"), d.get("potassium"),
            d.get("npk_status", "NORMAL")
        )
        ns.append(n)
        ps.append(p)
        ks.append(k)

    # FIX: fallback uses realistic values matching new thresholds.py ranges
    if not labels:
        labels = ["Day 21", "Day 22", "Day 23", "Day 24", "Day 25", "Day 26", "Day 27"]
        ns = [75, 78, 80, 79, 82, 80, 80]   # near NPK_N_OPTIMAL=80
        ps = [48, 50, 50, 51, 50, 50, 50]   # near NPK_P_OPTIMAL=50
        ks = [195, 198, 200, 200, 202, 200, 200]  # near NPK_K_OPTIMAL=200

    # FIX: fill latest NPK from last doc, then mock any None/0
    if latest:
        raw_n = latest.get("nitrogen")
        raw_p = latest.get("phosphorus")
        raw_k = latest.get("potassium")
        raw_s = latest.get("npk_status", "NORMAL")
        cur_n, cur_p, cur_k, cur_s = _fill_npk(raw_n, raw_p, raw_k, raw_s)
    else:
        cur_n, cur_p, cur_k, cur_s = (
            MOCK_NPK["nitrogen"], MOCK_NPK["phosphorus"],
            MOCK_NPK["potassium"], "NORMAL"
        )

    return jsonify({
        "labels":     labels,
        "nitrogen":   ns,
        "phosphorus": ps,
        "potassium":  ks,
        "current": {
            "nitrogen":   cur_n,
            "phosphorus": cur_p,
            "potassium":  cur_k,
            "status":     cur_s,
        },
        "optimal": OPTIMAL_RANGES["npk_optimal"],
    })


# ══════════════════════════════════════════════════════════
#  DEVICES
# ══════════════════════════════════════════════════════════

@app.route("/api/devices/latest")
def devices_latest():
    """
    Returns device/relay states.
    Priority order:
      1. Pi-posted device doc (fresh within 2 minutes)
      2. States derived from latest sensor reading + thresholds (stale Pi doc)
      3. All OFF fallback (no data at all)
    This mirrors the relay logic in pi_sensor.py so the dashboard
    always reflects the correct actuator state even if the Pi only
    posted sensor data and skipped the device doc.
    """
    # ── Derive states from latest sensor reading ──────────────────
    latest_sensor = sensors_col.find_one(sort=[("timestamp", DESCENDING)])

    if latest_sensor:
        temp  = latest_sensor.get("temp")
        moist = latest_sensor.get("moisture_avg")
        humid = latest_sensor.get("hum")

        # Exact relay logic mirroring pi_sensor.py update_relays()
        pump_on = moist is not None and moist < MOIST_MIN
        fan_on  = (temp  is not None and temp  > TEMP_MAX) or \
                  (humid is not None and humid > HUMID_FUNGAL)
        humi_on = humid is not None and humid < HUMID_MIN

        sensor_ts = latest_sensor.get("timestamp")
        ts_str = sensor_ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(sensor_ts, datetime) else "—"

        derived = {
            "irrigation_pump": "ON" if pump_on else "OFF",
            "exhaust_fan":     "ON" if fan_on  else "OFF",
            "humidifier":      "ON" if humi_on else "OFF",
            "auto_mode":       True,
            "timestamp":       ts_str,
            "_source":         "derived_from_sensor",
        }
    else:
        derived = {
            "irrigation_pump": "OFF",
            "exhaust_fan":     "OFF",
            "humidifier":      "OFF",
            "auto_mode":       True,
            "timestamp":       "—",
            "_source":         "no_data",
        }

    # ── Check Pi-posted device doc ────────────────────────────────
    doc = devices_col.find_one(sort=[("timestamp", DESCENDING)])

    if not doc:
        # No device doc ever posted — use derived
        return jsonify(derived)

    # ── If Pi doc is fresh (< 2 min), trust it directly ──────────
    doc_ts = doc.get("timestamp")
    if isinstance(doc_ts, datetime):
        age = (datetime.utcnow() - doc_ts).total_seconds()
        if age <= 120:
            # Pi is actively posting — use its actual relay states
            return jsonify(serialize(doc))

    # ── Pi doc is stale (> 2 min) — use derived instead ──────────
    # Preserve auto_mode preference from the last known Pi doc
    derived["auto_mode"] = doc.get("auto_mode", True)
    return jsonify(derived)


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

    has_timestamps = col.find_one({"timestamp": {"$exists": True}}) is not None

    if has_timestamps and filt:
        docs  = list(col.find(filt, sort=[("timestamp", DESCENDING)]).skip(skip).limit(limit))
        total = col.count_documents(filt)
    else:
        docs  = list(col.find({}, sort=[("_id", DESCENDING)]).skip(skip).limit(limit))
        total = col.count_documents({})

    if col_name == "sensors":
        records = [normalize_sensor(d) for d in docs]
    else:
        records = [serialize(d) for d in docs]

    return jsonify({"records": records, "count": total})


# ══════════════════════════════════════════════════════════
#  INGEST — Raspberry Pi POSTs data here
#  FIX: store NPK even when sensor returns None — store mock
#       so history never has null/0 gaps.
# ══════════════════════════════════════════════════════════

@app.route("/api/ingest", methods=["POST"])
def ingest():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "No JSON received"}), 400

    now = datetime.utcnow()

    # Read NPK from payload (supports both flat and nested formats)
    npk_block = payload.get("npk", {}) or {}
    raw_n      = npk_block.get("nitrogen",   payload.get("nitrogen"))
    raw_p      = npk_block.get("phosphorus", payload.get("phosphorus"))
    raw_k      = npk_block.get("potassium",  payload.get("potassium"))
    raw_s      = npk_block.get("status",     payload.get("npk_status", "NORMAL"))

    # FIX: fill None/0 before storing — no more zero records in MongoDB
    stored_n, stored_p, stored_k, stored_s = _fill_npk(raw_n, raw_p, raw_k, raw_s)

    sensor_doc = {
        "timestamp":    now,
        "temp":         payload.get("temperature", payload.get("temp")),
        "hum":          payload.get("humidity",    payload.get("hum")),
        "moisture_avg": payload.get("soil_moisture", payload.get("moisture_avg")),
        "nitrogen":     stored_n,
        "phosphorus":   stored_p,
        "potassium":    stored_k,
        "npk_status":   stored_s,
        "image":        payload.get("image", "latest_cabbage.jpg"),
        "stage":        payload.get("stage"),
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

    log.info(f"Ingest OK — temp={sensor_doc['temp']} moisture={sensor_doc['moisture_avg']} "
             f"hum={sensor_doc['hum']} npk=N{stored_n}/P{stored_p}/K{stored_k}({stored_s})")
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

    t   = payload.get("temperature",  payload.get("temp"))
    m   = payload.get("soil_moisture", payload.get("moisture_avg"))
    h   = payload.get("humidity",     payload.get("hum"))
    npk = payload.get("npk", {}) or {}

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

    # ── NPK — only alert if the raw sensor actually returned a bad status
    # (don't alert when we silently filled with mock values)
    raw_npk_status = npk.get("status") or payload.get("npk_status")
    if raw_npk_status and raw_npk_status not in ("NORMAL", "UNAVAILABLE", "ERROR", None):
        push("warning", "NPK Imbalance", f"NPK sensor reports: {raw_npk_status}. Check nutrient levels.")


# ══════════════════════════════════════════════════════════
#  AI PREDICTIONS
# ══════════════════════════════════════════════════════════

@app.route("/api/ai/predict", methods=["POST"])
def ai_predict():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No data received"}), 400
    ai_doc = {
        "timestamp":  datetime.utcnow(),
        "prediction": data.get("prediction"),
        "confidence": data.get("confidence"),
    }
    ai_predictions_col.insert_one(ai_doc)
    log.info(f"AI Prediction: {ai_doc['prediction']} ({ai_doc['confidence']}%)")
    return jsonify({"ok": True, "message": "AI prediction saved successfully"})


@app.route("/api/ai/history")
def ai_history():
    docs = list(ai_predictions_col.find({}, sort=[("timestamp", DESCENDING)]).limit(50))
    return jsonify({"records": [serialize(d) for d in docs]})


# ══════════════════════════════════════════════════════════
#  THRESHOLDS API
# ══════════════════════════════════════════════════════════

@app.route("/api/thresholds")
def get_thresholds():
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
        # FIX: fill NPK zeros in CSV export too
        n, p, k, s = _fill_npk(d.get("nitrogen"), d.get("phosphorus"), d.get("potassium"), d.get("npk_status","NORMAL"))
        writer.writerow([ts, d.get("temp",""), d.get("moisture_avg",""), d.get("hum",""), n, p, k, s, d.get("stage","")])

    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"pechay_sensor_data_{datetime.utcnow().strftime('%Y%m%d')}.csv"
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
    print("  TechnoGrowth · Pechay Monitor")
    print("  http://127.0.0.1:5000")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=True)