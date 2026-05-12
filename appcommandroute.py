# ══════════════════════════════════════════════════════════════
#  COMMAND QUEUE  — paste these routes into app.py
#  sensor_reader.py polls these to receive manual toggle commands
#  from the frontend and to report auto-mode state.
# ══════════════════════════════════════════════════════════════

# Add this import at the top of app.py alongside the existing ones:
#   from bson import ObjectId   ← already present
#   import uuid                 ← add this

import uuid   # for command IDs

# ── Store for auto-mode state (in-memory; survives restarts via MongoDB)
# Call GET /api/devices/command to read auto mode state
