# ============================================================
# ITT569 - Classification Server v3
# Changes from v2:
#   - Swapped MobileNetV2 for YOLOv8 custom monkey model
#   - Auto-logs every detection to CSV inside the project folder
#   - Draws bounding boxes on saved images when monkey detected
# ============================================================
# Requirements:
#   pip install flask flask-cors ultralytics pillow requests
# ============================================================

import io
import os
import csv
import logging
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
from dotenv import load_dotenv

try:
    from flask_cors import CORS
except Exception:  # pragma: no cover - fallback for minimal environments
    CORS = None

# Load environment variables from .env in project root (if present)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# ── Telegram config ───────────────────────────────────────────
# Set these before running the server:
#   $env:TELEGRAM_TOKEN="<your_bot_token>"
#   $env:TELEGRAM_CHAT_ID="<your_chat_id>"
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Paths ─────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PROJECT_DIR)
BASE_FOLDER = os.path.join(PROJECT_DIR, "captures")
MODEL_CANDIDATES = [
    os.path.join(PARENT_DIR, "monkeymodel", "monkey-guard", "backend", "models", "best.pt"),
    r"C:\Users\Hafiy Imran\Desktop\ITT569 - IoT\monkeymodel\monkey-guard\backend\models\best.pt"
]
MODEL_PATH = next((path for path in MODEL_CANDIDATES if os.path.exists(path)), MODEL_CANDIDATES[0])
CSV_LOG_PATH = os.path.join(PROJECT_DIR, "detection_log.csv")
os.makedirs(BASE_FOLDER, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Load YOLOv8 model ─────────────────────────────────────────
log.info(f"Loading YOLOv8 model from: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found at {MODEL_PATH}\n"
        "Create the folder Desktop/ITT569/models/ and place best.pt inside."
    )
model = YOLO(MODEL_PATH)
log.info("YOLOv8 model loaded.")

# ── CSV log setup ─────────────────────────────────────────────
CSV_HEADERS = [
    "test_number",
    "timestamp",
    "result",
    "confidence_pct",
    "num_detections",
    "image_size_bytes",
    "saved_image"
]

def init_csv():
    """Create CSV with headers if it does not exist."""
    os.makedirs(BASE_FOLDER, exist_ok=True)
    if not os.path.exists(CSV_LOG_PATH):
        try:
            with open(CSV_LOG_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
            log.info(f"CSV log created: {CSV_LOG_PATH}")
        except PermissionError as exc:
            log.warning(f"[CSV] Could not create primary log file: {exc}")


def get_next_test_number():
    """Read CSV and return next test number."""
    try:
        if not os.path.exists(CSV_LOG_PATH):
            return 1
        with open(CSV_LOG_PATH, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return len(rows) + 1
    except Exception as exc:
        log.warning(f"[CSV] Could not read log file: {exc}")
        return 1


def append_to_csv(row: dict):
    """Append one detection result row to the CSV, with a fallback file if needed."""
    target_path = CSV_LOG_PATH
    try:
        init_csv()
        with open(target_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow(row)
    except Exception as exc:
        fallback_path = os.path.join(BASE_FOLDER, "detection_log_fallback.csv")
        try:
            if not os.path.exists(fallback_path):
                with open(fallback_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                    writer.writeheader()
            with open(fallback_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writerow(row)
            log.warning(f"[CSV] Primary log unavailable; wrote to fallback: {fallback_path}")
        except Exception as fallback_exc:
            log.warning(f"[CSV] Logging failed completely: {fallback_exc}")

# ── Image saving with bounding boxes ──────────────────────────
def save_image(img_bytes, label, boxes=None):
    """
    Save image to Desktop/ITT569_captures.
    If boxes are provided, draw them on the image first.
    Returns the filename (not full path) for the CSV log.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{timestamp}_{label}.jpg"
    filepath  = os.path.join(BASE_FOLDER, filename)

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    if boxes:
        draw = ImageDraw.Draw(img)
        for (x1, y1, x2, y2), conf in boxes:
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            draw.text((x1, max(0, y1 - 15)),
                      f"monkey {conf:.0%}",
                      fill="red")

    img.save(filepath, "JPEG")
    log.info(f"[IMG] Saved: {filepath}")
    return filename

# ── Telegram alert ────────────────────────────────────────────
def send_telegram_alert(img_bytes, confidence, num_detections):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("[TG] Telegram not configured — set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID to enable alerts.")
        return
    try:
        caption = (
            f"MONKEY DETECTED\n"
            f"Detections: {num_detections}\n"
            f"Best confidence: {confidence:.1%}\n"
            f"System: ITT569 Farm Guard"
        )
        url   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {"photo": ("capture.jpg", img_bytes, "image/jpeg")}
        data  = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        resp  = requests.post(url, files=files, data=data, timeout=10)
        if resp.status_code == 200:
            log.info("[TG] Alert sent.")
        else:
            log.warning(f"[TG] Failed: {resp.text}. Check that the bot can message the provided chat ID.")
    except Exception as e:
        log.error(f"[TG] Error: {e}")


def test_telegram_connection():
    """Send a simple text message to verify the bot/chat configuration."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram token or chat ID is not set."

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "ITT569 Telegram test OK"
        }
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            return True, "Telegram test message sent successfully."
        return False, resp.text
    except Exception as exc:
        return False, str(exc)

# Flask app must be created before any route decorators are used
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
if CORS is not None:
    CORS(app)  # Enable CORS for frontend integration


@app.route("/test_telegram", methods=["GET"])
def http_test_telegram():
    ok, detail = test_telegram_connection()
    return (jsonify({"ok": ok, "detail": detail}), 200) if ok else (jsonify({"ok": ok, "detail": detail}), 400)


@app.route("/test_telegram_photo", methods=["GET"])
def http_test_telegram_photo():
    """Send the most recent saved image (if any) to Telegram for testing."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({"ok": False, "detail": "Telegram token or chat ID is not set."}), 400
    # find latest file in BASE_FOLDER and send; handle errors cleanly
    try:
        files = [f for f in os.listdir(BASE_FOLDER) if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg')]
        if not files:
            return jsonify({"ok": False, "detail": "No images in captures folder."}), 404
        latest = sorted(files)[-1]
        path = os.path.join(BASE_FOLDER, latest)
        with open(path, 'rb') as fh:
            img_bytes = fh.read()

        # send via same method as alerts
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {"photo": (latest, img_bytes, "image/jpeg")}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": f"Test photo: {latest}"}
        resp = requests.post(url, files=files, data=data, timeout=10)
        if resp.status_code == 200:
            return jsonify({"ok": True, "detail": "Photo sent."}), 200
        return jsonify({"ok": False, "detail": resp.text}), 400
    except Exception as exc:
        return jsonify({"ok": False, "detail": str(exc)}), 500


def get_telegram_updates():
    """Fetch getUpdates from Telegram and return parsed JSON or error."""
    if not TELEGRAM_TOKEN:
        return False, "TELEGRAM_TOKEN not set"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            return False, data
        return True, data
    except Exception as exc:
        return False, str(exc)


@app.route("/telegram_get_updates", methods=["GET"])
def http_telegram_get_updates():
    ok, data = get_telegram_updates()
    if not ok:
        return jsonify({"ok": False, "detail": data}), 400

    # Extract candidate chat IDs from updates
    results = data.get("result", [])
    chat_ids = set()
    for item in results:
        # messages
        msg = item.get("message") or item.get("edited_message") or item.get("channel_post")
        if msg:
            chat = msg.get("chat")
            if chat and "id" in chat:
                chat_ids.add(chat.get("id"))
        # callback_query
        cb = item.get("callback_query")
        if cb and cb.get("message") and cb.get("from"):
            frm = cb.get("from")
            if "id" in frm:
                chat_ids.add(frm.get("id"))

    chat_list = sorted(list(chat_ids))
    suggested = chat_list[-1] if chat_list else None
    return jsonify({"ok": True, "updates_count": len(results), "chat_ids": chat_list, "suggested_chat_id": suggested, "raw": data})

# (Flask app initialized earlier)

@app.route("/classify", methods=["POST"])
def classify():
    img_bytes = request.data
    if not img_bytes:
        return "error", 400

    test_num  = get_next_test_number()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"--- Test #{test_num} | {timestamp} | {len(img_bytes)} bytes ---")

    try:
        # Convert bytes to PIL image for YOLO
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # Run YOLOv8 inference
        results = model(img, conf=0.5, imgsz=640, verbose=False)
        result  = results[0]

        boxes_data    = []   # list of ((x1,y1,x2,y2), conf) for drawing
        best_conf     = 0.0
        num_detections = len(result.boxes)

        for box in result.boxes:
            coords = box.xyxy[0].tolist()   # [x1, y1, x2, y2]
            conf   = float(box.conf[0])
            boxes_data.append((coords, conf))
            if conf > best_conf:
                best_conf = conf

        is_monkey = num_detections > 0

        if is_monkey:
            label = "monkey"
            log.info(f"MONKEY DETECTED | {num_detections} box(es) | best conf {best_conf:.2%}")
            filename = save_image(img_bytes, label, boxes=boxes_data)
            send_telegram_alert(img_bytes, best_conf, num_detections)
        else:
            label    = "clear"
            best_conf = 0.0
            filename = save_image(img_bytes, label)
            log.info("Result: clear")

        # Log to CSV
        append_to_csv({
            "test_number":      test_num,
            "timestamp":        timestamp,
            "result":           label,
            "confidence_pct":   f"{best_conf * 100:.1f}",
            "num_detections":   num_detections,
            "image_size_bytes": len(img_bytes),
            "saved_image":      filename
        })

        return label, 200

    except Exception as e:
        log.error(f"Classification error: {e}")
        return "error", 500


@app.route("/health", methods=["GET"])
def health():
    return "ITT569 YOLOv8 server running", 200


@app.route("/api/stats", methods=["GET"])
def api_stats():
    rows = []
    if os.path.exists(CSV_LOG_PATH):
        with open(CSV_LOG_PATH, "r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    total = len(rows)
    monkey = sum(1 for row in rows if row.get("result") == "monkey")
    clear = sum(1 for row in rows if row.get("result") == "clear")
    confidences = [float(row.get("confidence_pct", 0) or 0) for row in rows if row.get("result") == "monkey"]
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    return jsonify({
        "total": total,
        "monkey": monkey,
        "clear": clear,
        "avg_conf": avg_conf
    })


@app.route("/api/logs", methods=["GET"])
def api_logs():
    rows = []
    if os.path.exists(CSV_LOG_PATH):
        with open(CSV_LOG_PATH, "r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    return jsonify(rows)


@app.route("/api/images/<path:filename>", methods=["GET"])
def api_image(filename):
    return send_from_directory(BASE_FOLDER, filename)


if __name__ == "__main__":
    init_csv()
    log.info(f"Captures saved to: {BASE_FOLDER}")
    log.info(f"Detection log CSV: {CSV_LOG_PATH}")
    log.info("Starting server on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)