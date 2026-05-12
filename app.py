import uuid 
from flask import Flask, render_template, jsonify, request, Response
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from bson import ObjectId
import uuid   # for command IDs
from datetime import datetime, timedelta
import csv, io, os, logging

# ── LOAD ENVIRONMENT ──
app = Flask(__name__)
CORS(app)
 
# ── MongoDB ──────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["cabbage_monitor"]
 
sensors_col    = db["sensors"]
alerts_col     = db["alerts"]
devices_col    = db["devices"]
npk_trends_col = db["npk_trends"]
 
# ── Helpers ──────────────────────────────────────────────
def serialize(doc):
    """Convert MongoDB doc to JSON-safe dict."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc
 
def days_filter(days_str):
    """Return a MongoDB timestamp filter dict or empty dict."""
    try:
        days = int(days_str)
        since = datetime.utcnow() - timedelta(days=days)
        return {"timestamp": {"$gte": since}}
    except (TypeError, ValueError):
        return {}
 
# ── /api/sensors/latest ──────────────────────────────────
@app.route("/api/sensors/latest")
def sensors_latest():
    """Most recent sensor reading (temp, moisture, humidity, NPK, stage)."""
    doc = sensors_col.find_one(sort=[("timestamp", DESCENDING)])
    if not doc:
        return jsonify({}), 404
    return jsonify(serialize(doc))
 
# ── /api/sensors (paginated list) ────────────────────────
@app.route("/api/sensors")
def sensors_list():
    limit = min(int(request.args.get("limit", 50)), 200)
    skip  = int(request.args.get("skip", 0))
    filt  = days_filter(request.args.get("days"))
    docs  = list(sensors_col.find(filt, sort=[("timestamp", DESCENDING)]).skip(skip).limit(limit))
    total = sensors_col.count_documents(filt)
    return jsonify({"records": [serialize(d) for d in docs], "count": total})
 
# ── /api/history (7-day arrays for charts) ───────────────
@app.route("/api/history")
def history():
    """
    Returns parallel arrays of daily averages for the last 7 days.
    Includes: temperature, soil_moisture, humidity, NPK labels.
    """
    since  = datetime.utcnow() - timedelta(days=7)
    docs   = list(sensors_col.find({"timestamp": {"$gte": since}},
                                    sort=[("timestamp", DESCENDING)]))
 
    # Bucket by date label
    buckets = {}
    for d in docs:
        ts = d.get("timestamp")
        label = ts.strftime("Day %d") if isinstance(ts, datetime) else "?"
        buckets.setdefault(label, {"temp": [], "moist": [], "humid": []})
        if d.get("temperature")  is not None: buckets[label]["temp"].append(d["temperature"])
        if d.get("soil_moisture") is not None: buckets[label]["moist"].append(d["soil_moisture"])
        if d.get("humidity")     is not None: buckets[label]["humid"].append(d["humidity"])
 
    labels, temps, moists, humids = [], [], [], []
    for label, vals in sorted(buckets.items()):
        labels.append(label)
        temps.append(round(sum(vals["temp"])  / len(vals["temp"]),  1) if vals["temp"]  else None)
        moists.append(round(sum(vals["moist"])/ len(vals["moist"]), 1) if vals["moist"] else None)
        humids.append(round(sum(vals["humid"])/ len(vals["humid"]), 1) if vals["humid"] else None)
 
    # Fallback demo data when DB is empty
    if not labels:
        labels = ["Day 21","Day 22","Day 23","Day 24","Day 25","Day 26","Day 27"]
        temps  = [28.1, 28.6, 29.0, 28.8, 29.4, 29.1, 29.0]
        moists = [54,   51,   48,   45,   40,   43,   42  ]
        humids = [78,   76,   80,   82,   79,   75,   77  ]
 
    return jsonify({
        "labels":        labels,
        "temperature":   temps,
        "soil_moisture": moists,
        "humidity":      humids,
        "temp_optimal":  {"min": 25, "max": 30},
        "moist_optimal": {"min": 43, "max": 60},
        "humid_optimal": {"min": 70, "max": 85},
    })
 
# ── /api/npk-trend ───────────────────────────────────────
@app.route("/api/npk-trend")
def npk_trend():
    since = datetime.utcnow() - timedelta(days=7)
    docs  = list(npk_trends_col.find({"timestamp": {"$gte": since}},
                                      sort=[("timestamp", ASCENDING := 1)]))
    latest = npk_trends_col.find_one(sort=[("timestamp", DESCENDING)])
 
    labels, ns, ps, ks = [], [], [], []
    for d in docs:
        ts = d.get("timestamp")
        labels.append(ts.strftime("Day %d") if isinstance(ts, datetime) else "?")
        ns.append(d.get("nitrogen"))
        ps.append(d.get("phosphorus"))
        ks.append(d.get("potassium"))
 
    if not labels:
        labels = ["Day 21","Day 22","Day 23","Day 24","Day 25","Day 26","Day 27"]
        ns = [42,43,44,44,45,45,45]
        ps = [30,31,31,32,32,32,32]
        ks = [26,26,27,27,28,28,28]
 
    current = serialize(latest) if latest else {"nitrogen":45,"phosphorus":32,"potassium":28,"status":"NORMAL"}
 
    return jsonify({
        "labels":     labels,
        "nitrogen":   ns,
        "phosphorus": ps,
        "potassium":  ks,
        "current":    current,
        "optimal":    {"nitrogen": 50, "phosphorus": 35, "potassium": 30},
    })
 
# ── /api/devices/latest ──────────────────────────────────
@app.route("/api/devices/latest")
def devices_latest():
    doc = devices_col.find_one(sort=[("timestamp", DESCENDING)])
    if not doc:
        return jsonify({"irrigation_pump":"OFF","exhaust_fan":"OFF","auto_mode":True,"timestamp":"—"})
    return jsonify(serialize(doc))
 
# ── /api/alerts ──────────────────────────────────────────
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
 
@app.route("/api/alerts/mark-all-read", methods=["POST"])
def mark_all_read():
    alerts_col.update_many({"read": False}, {"$set": {"read": True}})
    return jsonify({"ok": True})
 
# ── /api/logs (history log, multi-collection) ────────────
@app.route("/api/logs")
def logs():
    col_name = request.args.get("collection", "sensors")
    limit    = min(int(request.args.get("limit", 50)), 200)
    filt     = days_filter(request.args.get("days"))
 
    col_map  = {
        "sensors":    sensors_col,
        "alerts":     alerts_col,
        "devices":    devices_col,
        "npk_trends": npk_trends_col,
    }
    col = col_map.get(col_name, sensors_col)
    docs  = list(col.find(filt, sort=[("timestamp", DESCENDING)]).limit(limit))
    total = col.count_documents(filt)
    return jsonify({"records": [serialize(d) for d in docs], "count": total})
 
# ── /api/ingest  (Pi posts data here) ────────────────────
@app.route("/api/ingest", methods=["POST"])
def ingest():
    """
    Raspberry Pi posts JSON:
    {
      "temperature": 28.4,
      "soil_moisture": 52,
      "humidity": 76,          <-- NEW
      "npk": {"nitrogen":45, "phosphorus":32, "potassium":28, "status":"NORMAL"},
      "stage": "Head Formation",
      "irrigation_pump": "OFF",
      "exhaust_fan": "ON",
      "auto_mode": true
    }
    """
    payload = request.get_json(force=True)
    now = datetime.utcnow()
 
    # Sensor reading
    sensor_doc = {
        "timestamp":    now,
        "temperature":  payload.get("temperature"),
        "soil_moisture":payload.get("soil_moisture"),
        "humidity":     payload.get("humidity"),       # humidity field
        "npk":          payload.get("npk", {}),
        "stage":        payload.get("stage"),
    }
    sensors_col.insert_one(sensor_doc)
 
    # Device state snapshot
    device_doc = {
        "timestamp":       now,
        "irrigation_pump": payload.get("irrigation_pump", "OFF"),
        "exhaust_fan":     payload.get("exhaust_fan", "OFF"),
        "auto_mode":       payload.get("auto_mode", True),
    }
    devices_col.insert_one(device_doc)
 
    # NPK trend
    npk = payload.get("npk")
    if npk:
        npk_trends_col.insert_one({
            "timestamp":  now,
            "nitrogen":   npk.get("nitrogen"),
            "phosphorus": npk.get("phosphorus"),
            "potassium":  npk.get("potassium"),
            "status":     npk.get("status", "NORMAL"),
        })
 
    # Auto-generate alerts
    _auto_alert(now, payload)
 
    return jsonify({"ok": True, "timestamp": now.isoformat()})
 
def _auto_alert(now, payload):
    """Insert threshold alerts automatically on ingest."""
    def push(atype, title, desc):
        if not alerts_col.find_one({"title": title, "read": False}):
            alerts_col.insert_one({"timestamp": now, "type": atype,
                                   "title": title, "desc": desc, "read": False})
 
    t = payload.get("temperature")
    m = payload.get("soil_moisture")
    h = payload.get("humidity")
 
    if t is not None:
        if t > 30:   push("warning", "Temperature High", f"Temperature is {t}°C — above safe limit of 30°C.")
        elif t < 25: push("warning", "Temperature Low",  f"Temperature is {t}°C — below optimal range.")
 
    if m is not None:
        if m < 35:   push("warning", "Soil Moisture Critical", f"Soil moisture is {m}% — critically low. Irrigate now.")
        elif m < 43: push("warning", "Soil Moisture Low",      f"Soil moisture is {m}% — below optimal 43%.")
        elif m > 60: push("warning", "Soil Moisture High",     f"Soil moisture is {m}% — above optimal 60%.")
 
    if h is not None:
        if h < 60:   push("warning", "Humidity Critical Low", f"Air humidity is {h}% — critically low. Risk of wilting.")
        elif h < 70: push("warning", "Humidity Low",          f"Air humidity is {h}% — below optimal 70%.")
        elif h > 90: push("warning", "Humidity High",         f"Air humidity is {h}% — above 90%. Fungal risk.")
 
    npk = payload.get("npk", {})
    if npk.get("status") and npk["status"] != "NORMAL":
        push("warning", "NPK Imbalance", f"NPK sensor reports: {npk['status']}.")
 
# ── /export/csv ──────────────────────────────────────────
@app.route("/export/csv")
def export_csv():
    since = datetime.utcnow() - timedelta(days=30)
    docs  = list(sensors_col.find({"timestamp": {"$gte": since}},
                                   sort=[("timestamp", DESCENDING)]).limit(500))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Timestamp","Temperature (°C)","Soil Moisture (%)","Humidity (%)","N","P","K","NPK Status","Stage"])
    for d in docs:
        npk = d.get("npk", {})
        ts  = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(d.get("timestamp"), datetime) else ""
        writer.writerow([
            ts,
            d.get("temperature", ""),
            d.get("soil_moisture", ""),
            d.get("humidity", ""),          # humidity in CSV
            npk.get("nitrogen", ""),
            npk.get("phosphorus", ""),
            npk.get("potassium", ""),
            npk.get("status", ""),
            d.get("stage", ""),
        ])
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"cabbage_sensor_data_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    )
 
# ── Health check ─────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)