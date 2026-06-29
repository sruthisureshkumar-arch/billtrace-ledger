import io
import json
import os
import random
import re
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Use a stable secret key from environment so sessions survive restarts.
# On first deploy, set FLASK_SECRET_KEY in Azure App Service → Configuration.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

# ---- Security config ----
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ---- Rate limiter ----
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["300 per day", "60 per hour"],
    storage_uri="memory://",
)

# ---- Security headers on every response ----
@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ---- Error handlers ----
@app.errorhandler(413)
def upload_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 10 MB."}), 413

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Too many requests. Please wait and try again."}), 429

# ---- Auth decorator ----
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated

# ---- Image validation (magic bytes — not just extension) ----
_IMAGE_SIGNATURES = [
    b"\xff\xd8\xff",           # JPEG
    b"\x89PNG\r\n\x1a\n",     # PNG
    b"RIFF",                   # WebP (bytes 0-3; bytes 8-11 = "WEBP")
    b"GIF8",                   # GIF
]

def _is_valid_image(data: bytes) -> bool:
    return any(data.startswith(sig) for sig in _IMAGE_SIGNATURES)

LEDGER_FILE = Path(__file__).parent / "ledger.json"
USERS_FILE = Path(__file__).parent / "users.json"

issued_series_log = {
    "A1B2C3D4": "Verified",
    "X9Y8Z7W6": "Verified",
    "FLAG1234": "Verified",
    "M5N6O7P8": "Verified",
    "Q3R4S5T6": "Verified",
}

LOCATIONS = [
    {"lat": 40.7128, "lon": -74.0060, "name": "New York, NY"},
    {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"},
    {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix, AZ"},
]

DUMMY_SERIALS = ["A1B2C3D4", "X9Y8Z7W6", "FLAG1234", "M5N6O7P8", "FAKE9999", "UNK00001"]

def load_ledger() -> dict:

    if LEDGER_FILE.exists():
        try:
            data = json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "all_scanned_bills" in data:
                return data["all_scanned_bills"]
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_ledger(all_scanned_bills: dict) -> None:
   
    payload = {"all_scanned_bills": all_scanned_bills}
    LEDGER_FILE.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )


all_scanned_bills: dict = load_ledger()

def load_users() -> dict:
    
    if USERS_FILE.exists():
        try:
            data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_users(users: dict) -> None:
   
    USERS_FILE.write_text(
        json.dumps(users, indent=2, default=str), encoding="utf-8"
    )


registered_users: dict = load_users()

def _azure_vision_ocr(image_bytes: bytes) -> str:
    """Extract serial number from a currency note image using Azure Computer Vision."""
    key = os.environ.get("AZURE_VISION_KEY", "")
    endpoint = os.environ.get("AZURE_VISION_ENDPOINT", "")

    if not key or not endpoint:
        app.logger.warning("Azure Vision credentials not set — falling back to dummy serial.")
        return ""

    try:
        from azure.cognitiveservices.vision.computervision import ComputerVisionClient
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        from msrest.authentication import CognitiveServicesCredentials

        client = ComputerVisionClient(endpoint.rstrip("/"), CognitiveServicesCredentials(key))
        stream = io.BytesIO(image_bytes)

        read_response = client.read_in_stream(stream, raw=True)
        operation_id = read_response.headers["Operation-Location"].split("/")[-1]

        # Poll until complete (max ~10 s)
        for _ in range(10):
            result = client.get_read_result(operation_id)
            if result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
                break
            time.sleep(1)

        if result.status != OperationStatusCodes.succeeded:
            return ""

        # Collect every line of text Azure found
        lines = []
        for page in result.analyze_result.read_results:
            for line in page.lines:
                lines.append(line.text.strip().upper())

        full_text = " ".join(lines)

        # Try to match common currency serial patterns first
        # US Federal Reserve notes: letter + 8 digits + letter  e.g. "A12345678B"
        # Some notes: 2 letters + 8 digits  e.g. "AB12345678"
        patterns = [
            r'\b[A-Z]\d{8}[A-Z]\b',      # classic US format
            r'\b[A-Z]{2}\d{8}\b',          # alternate format
            r'\b[A-Z0-9]{8,12}\b',         # generic fallback
        ]
        for pattern in patterns:
            matches = re.findall(pattern, full_text)
            if matches:
                return max(matches, key=len)[:20]

        # Last resort: longest alphanumeric token ≥ 4 chars
        tokens = re.findall(r'[A-Z0-9]{4,}', full_text)
        if tokens:
            return max(tokens, key=len)[:20]

        return ""

    except Exception as exc:
        app.logger.warning(f"Azure Vision OCR error: {exc}")
        return ""


def simulate_ocr(has_image: bool, image_bytes: bytes = None, manual_serial=None):
    if manual_serial and manual_serial.strip():
        return "".join(c for c in manual_serial.strip().upper() if c.isalnum())[:20]
    if has_image and image_bytes:
        extracted = _azure_vision_ocr(image_bytes)
        if extracted:
            return extracted
        # Azure not configured — fall back to a dummy serial for demo purposes
        return random.choice(DUMMY_SERIALS)
    return ""

def simulate_gps(location_index=None):
   
    if location_index is not None and 0 <= location_index < len(LOCATIONS):
        return LOCATIONS[location_index]
    return random.choice(LOCATIONS)

def check_bill(serial: str, current_timestamp: datetime, current_location: dict) -> dict:

    result = {
        "serial": serial,
        "timestamp": current_timestamp.isoformat(),
        "location": current_location,
        "status": "",
        "status_code": "",
        "message": "",
        "history": [],
        "clone_alert": False,
    }

    if serial not in issued_series_log:
        result["status"] = "INVALID"
        result["status_code"] = "red"
        result["message"] = (
            "Serial number series unrecognized. "
            "This note is NOT in the verified issuance database."
        )
       
        current_user = session.get("username", "unknown")
        scan_record = {
            "timestamp": current_timestamp.isoformat(),
            "location": current_location,
            "user": current_user,
        }
        all_scanned_bills.setdefault(serial, []).append(scan_record)
        save_ledger(all_scanned_bills)
        result["history"] = all_scanned_bills.get(serial, [])
        return result

    previous_scans = all_scanned_bills.get(serial, [])
    clone_detected = False

    if previous_scans:
        most_recent = previous_scans[-1]
        prev_time = datetime.fromisoformat(most_recent["timestamp"])
        prev_loc = most_recent["location"]

        time_delta = current_timestamp - prev_time
        location_differs = (
            current_location["lat"] != prev_loc["lat"]
            or current_location["lon"] != prev_loc["lon"]
        )

        if time_delta < timedelta(hours=1) and location_differs:
            clone_detected = True

    current_user = session.get("username", "unknown")
    scan_record = {
        "timestamp": current_timestamp.isoformat(),
        "location": current_location,
        "user": current_user,
    }
    all_scanned_bills.setdefault(serial, []).append(scan_record)
    save_ledger(all_scanned_bills)

    if clone_detected:
        result["status"] = "CLONE ALERT"
        result["status_code"] = "yellow"
        result["message"] = (
            "Potential Cloned Note Detected! "
            "Previously scanned within one hour at a different location. "
            "Exercise extreme caution."
        )
        result["clone_alert"] = True
    else:
        result["status"] = "VERIFIED"
        result["status_code"] = "green"
        if len(previous_scans) == 0:
            result["message"] = "Note verified. First scan recorded successfully."
        else:
            result["message"] = (
                "Note verified. Valid interval since last scan — no anomaly detected."
            )

    result["history"] = all_scanned_bills.get(serial, [])
    return result

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login_page"))
    return render_template("index.html", username=session["username"])


@app.route("/login")
def login_page():
    if "username" in session:
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/api/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400

    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400

    if username.lower() in {k.lower() for k in registered_users}:
        return jsonify({"error": "Username already taken."}), 409

    registered_users[username] = generate_password_hash(password, method="pbkdf2:sha256")
    save_users(registered_users)

    session["username"] = username
    return jsonify({"message": "Account created successfully!", "username": username})


@app.route("/api/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    stored_hash = registered_users.get(username)
    if not stored_hash or not check_password_hash(stored_hash, password):
        return jsonify({"error": "Invalid username or password."}), 401

    session["username"] = username
    return jsonify({"message": "Login successful!", "username": username})


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login_page"))


@app.route("/api/process", methods=["POST"])
@login_required
@limiter.limit("15 per minute")
def process_scan():
    image_bytes = None
    has_image = "image" in request.files and request.files["image"].filename != ""
    if has_image:
        image_bytes = request.files["image"].read()
        if not _is_valid_image(image_bytes):
            return jsonify({"error": "Invalid file type. Please upload a JPEG, PNG, or WebP image."}), 400

    manual_serial = request.form.get("serial", "").strip()
    location_index_str = request.form.get("location_index", "")

    location_index = None
    if location_index_str.isdigit():
        location_index = int(location_index_str)

    serial = simulate_ocr(has_image, image_bytes, manual_serial if manual_serial else None)

    if not serial:
        return jsonify({"error": "No serial number could be extracted. Please upload an image or enter a serial number manually."}), 400

    current_timestamp = datetime.now()
    current_location = simulate_gps(location_index)

    result = check_bill(serial, current_timestamp, current_location)

    return jsonify(result)


@app.route("/api/history", methods=["GET"])
@login_required
@limiter.limit("30 per minute")
def get_history():
    history = []
    for serial, scans in all_scanned_bills.items():
        for scan in scans:
            verified = serial in issued_series_log
            history.append({
                "serial": serial,
                "timestamp": scan["timestamp"],
                "location": scan["location"],
                "user": scan.get("user", "unknown"),
                "verified": verified,
            })
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"history": history, "total_scans": len(history)})


@app.route("/api/locations", methods=["GET"])
def get_locations():
    return jsonify({"locations": LOCATIONS})


@app.route("/api/reset", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def reset_ledger():
    global all_scanned_bills
    all_scanned_bills = {}
    save_ledger(all_scanned_bills)
    return jsonify({"message": "Ledger reset successfully."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
