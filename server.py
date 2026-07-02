# ============================================================
# ITT569 - Classification Server v3
# Changes from v2:
#   - Swapped MobileNetV2 for YOLOv8 custom monkey model
#   - Auto-logs every detection to CSV on Desktop
#   - Draws bounding boxes on saved images when monkey detected
# ============================================================
# Requirements:
#   pip install flask ultralytics pillow requests
#
# Place your trained model at:
#   C:\Users\Hafiy Imran\Desktop\ITT569\models\best.pt
# ============================================================

import io
import os
import csv
import logging
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# ── Telegram config ───────────────────────────────────────────
# Set these before running the server:
#   $env:TELEGRAM_TOKEN="<your_bot_token>"
#   $env:TELEGRAM_CHAT_ID="<your_chat_id>"
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", ".")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", ".")

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
BASE_FOLDER   = os.path.join(BASE_DIR, "capture_image")
MODEL_PATH    = os.path.join(BASE_DIR, "models", "best.pt")
CSV_LOG_PATH  = os.path.join(BASE_FOLDER, "detection_log.csv")
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
    if not os.path.exists(CSV_LOG_PATH):
        with open(CSV_LOG_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
        log.info(f"CSV log created: {CSV_LOG_PATH}")

def get_next_test_number():
    """Read CSV and return next test number."""
    if not os.path.exists(CSV_LOG_PATH):
        return 1
    with open(CSV_LOG_PATH, "r") as f:
        rows = list(csv.DictReader(f))
    return len(rows) + 1

def append_to_csv(row: dict):
    """Append one detection result row to the CSV."""
    with open(CSV_LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row)

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
    if (
        TELEGRAM_TOKEN in {"YOUR_TELEGRAM_BOT_TOKEN", ""}
        or TELEGRAM_CHAT_ID in {"YOUR_CHAT_ID", ""}
    ):
        log.warning("[TG] Telegram not configured — skipping.")
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
            log.warning(f"[TG] Failed: {resp.text}")
    except Exception as e:
        log.error(f"[TG] Error: {e}")

# ── Flask app ─────────────────────────────────────────────────
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

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

# ── API Endpoints for Dashboard ───────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Return all detection logs as JSON."""
    if not os.path.exists(CSV_LOG_PATH):
        return jsonify([])
    try:
        with open(CSV_LOG_PATH, "r") as f:
            rows = list(csv.DictReader(f))
        return jsonify(rows)
    except Exception as e:
        log.error(f"Error reading logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Calculate and return quick stats for dashboard KPI cards."""
    if not os.path.exists(CSV_LOG_PATH):
        return jsonify({"total": 0, "monkey": 0, "clear": 0, "avg_conf": 0.0})
    try:
        with open(CSV_LOG_PATH, "r") as f:
            rows = list(csv.DictReader(f))
        
        total = len(rows)
        monkey = sum(1 for r in rows if r.get("result") == "monkey")
        clear = total - monkey
        
        confidences = [float(r.get("confidence_pct", 0)) for r in rows if r.get("result") == "monkey"]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return jsonify({
            "total": total,
            "monkey": monkey,
            "clear": clear,
            "avg_conf": round(avg_conf, 1)
        })
    except Exception as e:
        log.error(f"Error calculating stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/images/<filename>", methods=["GET"])
def get_image(filename):
    """Serve saved images from the capture folder."""
    return send_from_directory(BASE_FOLDER, filename)


if __name__ == "__main__":
    init_csv()
    log.info(f"Captures saved to: {BASE_FOLDER}")
    log.info(f"Detection log CSV: {CSV_LOG_PATH}")
    log.info("Starting server on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)