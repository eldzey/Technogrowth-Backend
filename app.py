import uuid 
from flask import Flask, render_template, jsonify, request, Response
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from bson import ObjectId
import uuid   # for command IDs
from datetime import datetime, timedelta
import csv, io, os, logging

# ── LOAD ENVIRONMENT ──
load_dotenv()

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("TechnoGrowth")

# ── FLASK + MONGO ──
app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI")

app.config["MONGO_URI"] = MONGO_URI

try:
    mongo = PyMongo(app)
    log.info("MongoDB connected successfully.")
except Exception as e:
    log.error(f"MongoDB connection failed: {e}")
    raise

# ── HELPERS ──
def serialize(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc

def serialize_all(docs):
    return [serialize(d) for d in docs]

def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def parse_limit(default=50, maximum=500):
    try:
        return min(int(request.args.get("limit", default)), maximum)
    except ValueError:
        return default

def days_filter(days_arg):
    """Return a MongoDB $gte timestamp filter dict, or {} for all time."""
    if not days_arg:
        return {}
    try:
        cutoff = datetime.utcnow() - timedelta(days=int(days_arg))
        return {"timestamp": {"$gte": cutoff.strftime("%Y-%m-%d %H:%M:%S")}}
    except ValueError:
        return {}

# ── ERROR HANDLERS ──
@app.errorhandler(Exception)
def handle_exception(e):
    log.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

# ── FRONTEND ──
@app.route("/")
def dashboard():
    return render_template("index.html")

# ══════════════════════════════════════════════════════════
#  SENSORS
# ══════════════════════════════════════════════════════════
@app.route("/api/sensors", methods=["POST"])
def post_sensors():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    data["timestamp"] = now_str()
    result = mongo.db.sensors.insert_one(data)
    log.info(f"Sensor reading saved: {result.inserted_id}")
    return jsonify({"status": "saved", "id": str(result.inserted_id)}), 201

@app.route("/api/sensors/latest")
def sensors_latest():
    doc = mongo.db.sensors.find_one(sort=[("timestamp", -1)])
    if not doc:
        return jsonify({"error": "No sensor data yet"}), 404
    return jsonify(serialize(doc))

@app.route("/api/sensors/history")
def sensors_history():
    limit = parse_limit(50)
    docs = list(mongo.db.sensors.find().sort("timestamp", -1).limit(limit))
    return jsonify(serialize_all(docs))

# ══════════════════════════════════════════════════════════
#  DEVICES
# ══════════════════════════════════════════════════════════
@app.route("/api/devices", methods=["POST"])
def post_devices():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    data["timestamp"] = now_str()
    result = mongo.db.devices.insert_one(data)
    log.info(f"Device state saved: {result.inserted_id}")
    return jsonify({"status": "saved", "id": str(result.inserted_id)}), 201

@app.route("/api/devices/latest")
def devices_latest():
    doc = mongo.db.devices.find_one(sort=[("timestamp", -1)])
    if not doc:
        return jsonify({"error": "No device data yet"}), 404
    return jsonify(serialize(doc))

@app.route("/api/devices/history")
def devices_history():
    limit = parse_limit(50)
    docs = list(mongo.db.devices.find().sort("timestamp", -1).limit(limit))
    return jsonify(serialize_all(docs))

@app.route("/api/devices/command")
def get_device_command():
    """
    Returns current auto-mode state.
    sensor_reader.py polls this to decide whether to run auto_control().
    """
    doc = mongo.db.settings.find_one({"key": "auto_mode"})
    auto = doc["value"] if doc else True   # default: auto mode ON
    return jsonify({"auto_mode": auto})


# ── Frontend calls this when the auto-mode toggle changes
@app.route("/api/devices/auto-mode", methods=["POST"])
def set_auto_mode():
    data = request.get_json(silent=True)
    if data is None or "enabled" not in data:
        return jsonify({"error": "Missing 'enabled' field"}), 400

    enabled = bool(data["enabled"])
    mongo.db.settings.update_one(
        {"key": "auto_mode"},
        {"$set": {"key": "auto_mode", "value": enabled, "updated": now_str()}},
        upsert=True
    )
    log.info(f"Auto mode set to: {enabled}")
    return jsonify({"status": "ok", "auto_mode": enabled})


# ── Frontend calls this when the user clicks "Turn ON / Turn OFF"
@app.route("/api/devices/<device>/toggle", methods=["POST"])
def queue_device_toggle(device):
    """
    Queue a manual relay command for sensor_reader.py to pick up and execute.
    device: 'pump' or 'fan'
    Body:   {"state": "ON"} or {"state": "OFF"}
    """
    if device not in ("pump", "fan"):
        return jsonify({"error": "Unknown device. Use 'pump' or 'fan'."}), 400

    data = request.get_json(silent=True)
    if not data or "state" not in data or data["state"] not in ("ON", "OFF"):
        return jsonify({"error": "Body must be {\"state\": \"ON\"} or {\"state\": \"OFF\"}"}), 400

    # Check auto mode — manual commands are only valid when auto mode is OFF
    doc = mongo.db.settings.find_one({"key": "auto_mode"})
    auto = doc["value"] if doc else True
    if auto:
        return jsonify({"error": "Auto mode is active. Disable auto mode before manual control."}), 409

    command = {
        "id":        str(uuid.uuid4()),
        "device":    device,
        "state":     data["state"],
        "timestamp": now_str(),
        "acked":     False,
    }
    mongo.db.device_commands.insert_one(command)
    log.info(f"Queued command: {device.upper()} → {data['state']}")
    return jsonify({"status": "queued", "command_id": command["id"]}), 202


# ── sensor_reader.py polls this to get pending commands
@app.route("/api/devices/pending-commands")
def get_pending_commands():
    """Return all unacknowledged commands for sensor_reader.py to execute."""
    docs = list(mongo.db.device_commands.find({"acked": False}).sort("timestamp", 1))
    return jsonify(serialize_all(docs))


# ── sensor_reader.py calls this after it has applied each command
@app.route("/api/devices/ack-commands", methods=["POST"])
def ack_commands():
    """Mark commands as acknowledged so they aren't re-sent."""
    data = request.get_json(silent=True)
    if not data or "ids" not in data:
        return jsonify({"error": "Missing 'ids' list"}), 400

    result = mongo.db.device_commands.update_many(
        {"id": {"$in": data["ids"]}},
        {"$set": {"acked": True}}
    )
    log.info(f"Acknowledged {result.modified_count} command(s)")
    return jsonify({"status": "ok", "acked": result.modified_count})

# ══════════════════════════════════════════════════════════
#  ALERTS
# ══════════════════════════════════════════════════════════
@app.route("/api/alerts", methods=["POST"])
def post_alerts():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    required = {"type", "title", "desc", "sensor"}
    missing = required - data.keys()
    if missing:
        return jsonify({"error": f"Missing alert fields: {missing}"}), 400
    data["timestamp"] = now_str()
    data.setdefault("read", False)
    result = mongo.db.alerts.insert_one(data)
    log.warning(f"Alert saved [{data['type']}]: {data['title']}")
    return jsonify({"status": "saved", "id": str(result.inserted_id)}), 201

@app.route("/api/alerts")
def get_alerts():
    limit = parse_limit(50)
    query = {} if request.args.get("all") == "true" else {"read": False}
    docs = list(mongo.db.alerts.find(query).sort("timestamp", -1).limit(limit))
    return jsonify(serialize_all(docs))

@app.route("/api/alerts/<alert_id>/read", methods=["PATCH"])
def mark_alert_read(alert_id):
    try:
        oid = ObjectId(alert_id)
    except Exception:
        return jsonify({"error": "Invalid alert ID"}), 400
    result = mongo.db.alerts.update_one({"_id": oid}, {"$set": {"read": True}})
    if result.matched_count == 0:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"status": "marked as read"})

# FIX: frontend calls PATCH /api/alerts/mark-all-read
@app.route("/api/alerts/mark-all-read", methods=["PATCH"])
def mark_all_alerts_read():
    result = mongo.db.alerts.update_many({"read": False}, {"$set": {"read": True}})
    log.info(f"Marked {result.modified_count} alerts as read")
    return jsonify({"status": "ok", "modified": result.modified_count})

# FIX: frontend polls GET /api/alerts/unread-count
@app.route("/api/alerts/unread-count")
def alerts_unread_count():
    count = mongo.db.alerts.count_documents({"read": False})
    return jsonify({"count": count})

# ══════════════════════════════════════════════════════════
#  ANALYTICS  (FIX: frontend fetches /api/history and /api/npk-trend)
# ══════════════════════════════════════════════════════════
@app.route("/api/history")
def get_history():
    """
    Returns the last 7 sensor readings bucketed by day label for the
    environment charts (temperature + soil moisture trend lines).
    """
    docs = list(
        mongo.db.sensors.find().sort("timestamp", -1).limit(7)
    )
    docs.reverse()  # oldest first for chart x-axis

    labels        = []
    temperatures  = []
    soil_moisture = []

    for i, d in enumerate(docs):
        ts = d.get("timestamp", "")
        # Use "Day N" label when we can't parse the date
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            labels.append(dt.strftime("%-d %b"))
        except Exception:
            labels.append(f"Day {i + 1}")

        temperatures.append(d.get("temperature"))
        soil_moisture.append(d.get("soil_moisture"))

    # Fall back to dummy labels when the collection is empty
    if not labels:
        labels        = ["Day 21", "Day 22", "Day 23", "Day 24", "Day 25", "Day 26", "Day 27"]
        temperatures  = [28.1, 28.6, 29.0, 28.8, 29.4, 29.1, 29.0]
        soil_moisture = [54, 51, 48, 45, 40, 43, 42]

    return jsonify({
        "labels":        labels,
        "temperature":   temperatures,
        "soil_moisture": soil_moisture,
        "temp_optimal":  {"min": 25, "max": 30},
        "moist_optimal": {"min": 43, "max": 60},
    })

@app.route("/api/npk-trend")
def get_npk_trend():
    """
    Returns NPK time-series (last 7 readings) plus current and optimal
    snapshot for the bar chart.
    """
    docs = list(
        mongo.db.sensors.find(
            {"npk": {"$exists": True}},
            {"npk": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(7)
    )
    docs.reverse()

    labels     = []
    nitrogen   = []
    phosphorus = []
    potassium  = []

    for i, d in enumerate(docs):
        ts = d.get("timestamp", "")
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            labels.append(dt.strftime("%-d %b"))
        except Exception:
            labels.append(f"Day {i + 1}")
        npk = d.get("npk", {})
        nitrogen.append(npk.get("nitrogen"))
        phosphorus.append(npk.get("phosphorus"))
        potassium.append(npk.get("potassium"))

    if not labels:
        labels     = ["Day 21", "Day 22", "Day 23", "Day 24", "Day 25", "Day 26", "Day 27"]
        nitrogen   = [42, 43, 44, 44, 45, 45, 45]
        phosphorus = [30, 31, 31, 32, 32, 32, 32]
        potassium  = [26, 26, 27, 27, 28, 28, 28]

    # Current = last data point (or fallback)
    current = {
        "nitrogen":   nitrogen[-1]   if nitrogen   else 45,
        "phosphorus": phosphorus[-1] if phosphorus else 32,
        "potassium":  potassium[-1]  if potassium  else 28,
    }

    return jsonify({
        "labels":     labels,
        "nitrogen":   nitrogen,
        "phosphorus": phosphorus,
        "potassium":  potassium,
        "current":    current,
        "optimal":    {"nitrogen": 50, "phosphorus": 35, "potassium": 30},
    })

# ══════════════════════════════════════════════════════════
#  HISTORY LOG  (FIX: frontend fetches /api/logs)
# ══════════════════════════════════════════════════════════
# Maps the frontend <select> option values to actual Mongo collections.
COLLECTION_MAP = {
    "sensors":    "sensors",
    "alerts":     "alerts",
    "devices":    "devices",
    "npk_trends": "sensors",   # NPK trends come from the sensors collection
}

@app.route("/api/logs")
def get_logs():
    collection_key = request.args.get("collection", "sensors")
    collection_name = COLLECTION_MAP.get(collection_key)
    if not collection_name:
        return jsonify({"error": "Unknown collection"}), 400

    limit      = parse_limit(50)
    days_arg   = request.args.get("days", "")
    query      = days_filter(days_arg)

    # For the npk_trends view only include documents that have an npk field
    if collection_key == "npk_trends":
        query["npk"] = {"$exists": True}

    col   = mongo.db[collection_name]
    total = col.count_documents(query)
    docs  = list(col.find(query).sort("timestamp", -1).limit(limit))

    # For npk_trends, flatten the npk sub-document to top level for the table
    if collection_key == "npk_trends":
        flattened = []
        for d in docs:
            npk = d.get("npk", {})
            flattened.append({
                "_id":       str(d["_id"]),
                "timestamp": d.get("timestamp"),
                "nitrogen":  npk.get("nitrogen"),
                "phosphorus": npk.get("phosphorus"),
                "potassium": npk.get("potassium"),
                "status":    npk.get("status"),
            })
        return jsonify({"count": total, "records": flattened})

    return jsonify({"count": total, "records": serialize_all(docs)})

# ══════════════════════════════════════════════════════════
#  EXPORTS  (FIX: frontend links to /export/csv and /export/pdf)
# ══════════════════════════════════════════════════════════
@app.route("/export/csv")
def export_csv():
    """Export the last 500 sensor readings as a CSV download."""
    docs = list(mongo.db.sensors.find().sort("timestamp", -1).limit(500))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp", "temperature", "humidity",
        "soil_moisture", "npk_nitrogen", "npk_phosphorus", "npk_potassium", "npk_status"
    ])
    for d in docs:
        npk = d.get("npk", {})
        writer.writerow([
            d.get("timestamp"),
            d.get("temperature"),
            d.get("humidity"),
            d.get("soil_moisture"),
            npk.get("nitrogen"),
            npk.get("phosphorus"),
            npk.get("potassium"),
            npk.get("status"),
        ])

    output.seek(0)
    filename = f"technogrowth_sensors_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/export/pdf")
def export_pdf():
    """
    Placeholder PDF export — returns a 501 with a clear message.
    Replace the body with a real PDF generation library (e.g. WeasyPrint,
    ReportLab, or pdfkit) when needed.
    """
    return jsonify({
        "error": "PDF export not yet implemented",
        "hint":  "Install WeasyPrint or ReportLab and generate the report here."
    }), 501

# ══════════════════════════════════════════════════════════
#  STATUS
# ══════════════════════════════════════════════════════════
@app.route("/api/status")
def status():
    try:
        mongo.db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return jsonify({
        "status": "running",
        "time":   now_str(),
        "db":     db_status
    })

# ── MAIN ──
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)