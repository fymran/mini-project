# ============================================================
# ITT569 - Classification Server v2
# Changes from v1:
#   - Saves every captured image to Desktop with timestamp
#   - Logs top-5 predictions with confidence scores
#   - Telegram alert with image when monkey detected
# ============================================================
# Requirements:
#   pip install flask tensorflow pillow requests
# ============================================================

import io
import os
import logging
from datetime import datetime
import numpy as np
import requests
from flask import Flask, request
from PIL import Image
import tensorflow as tf

# ── Telegram config ───────────────────────────────────────────
TELEGRAM_TOKEN   = "8946920626:AAHCVPc32nvPcCHbEhUrr_eUQXtzk3_UHDg"
TELEGRAM_CHAT_ID = "780329978"

# ── Image save folder ─────────────────────────────────────────
# Saves captured images here so you can see what the camera sees
SAVE_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "ITT569_captures")
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ── App setup ─────────────────────────────────────────────────
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Load model ────────────────────────────────────────────────
log.info("Loading MobileNetV2...")
model = tf.keras.applications.MobileNetV2(weights="imagenet", include_top=True)
model.trainable = False
log.info("Model ready.")

# ImageNet primate class index range
MONKEY_CLASS_INDICES = set(range(365, 383))
CONFIDENCE_THRESHOLD = 0.15  # Lowered for printed photo testing


def preprocess_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize((224, 224))
    arr = np.array(img, dtype=np.float32)
    arr = tf.keras.applications.mobilenet_v2.preprocess_input(arr)
    return np.expand_dims(arr, axis=0)


def save_image(img_bytes, label):
    """Save captured image to Desktop/ITT569_captures with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{timestamp}_{label}.jpg"
    filepath  = os.path.join(SAVE_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    log.info(f"[IMG] Saved: {filepath}")
    return filepath


def send_telegram_alert(img_bytes, label, confidence):
    """Send captured image + alert to Telegram."""
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        log.warning("[TG] Telegram not configured — skipping alert.")
        return
    try:
        caption = (
            f"MONKEY DETECTED\n"
            f"Confidence: {confidence:.1%}\n"
            f"System: ITT569 Farm Guard"
        )
        url   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {"photo": ("capture.jpg", img_bytes, "image/jpeg")}
        data  = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        resp  = requests.post(url, files=files, data=data, timeout=10)
        if resp.status_code == 200:
            log.info("[TG] Alert sent successfully.")
        else:
            log.warning(f"[TG] Failed: {resp.text}")
    except Exception as e:
        log.error(f"[TG] Error: {e}")


@app.route("/classify", methods=["POST"])
def classify():
    img_bytes = request.data
    if not img_bytes:
        log.warning("Empty request.")
        return "error", 400

    log.info(f"--- New capture received: {len(img_bytes)} bytes ---")

    try:
        inp     = preprocess_image(img_bytes)
        preds   = model.predict(inp, verbose=0)
        decoded = tf.keras.applications.mobilenet_v2.decode_predictions(
                      preds, top=5)[0]

        # Print all top-5 so you can see what the model thinks
        log.info("Top-5 predictions:")
        for i, (wn_id, label, score) in enumerate(decoded, 1):
            marker = " <-- PRIMATE" if (int(np.argsort(preds[0])[::-1][i-1])
                                         in MONKEY_CLASS_INDICES) else ""
            log.info(f"  {i}. {label:30s} {score:.4f}{marker}")

        top_idx  = int(np.argmax(preds[0]))
        top_conf = float(preds[0][top_idx])
        is_monkey = (top_idx in MONKEY_CLASS_INDICES and
                     top_conf >= CONFIDENCE_THRESHOLD)

        result_label = "monkey" if is_monkey else "clear"

        # Always save the image so you can inspect it
        save_image(img_bytes, result_label)

        if is_monkey:
            log.info(f"MONKEY DETECTED — class {top_idx}, conf {top_conf:.2%}")
            send_telegram_alert(img_bytes, result_label, top_conf)
            return "monkey", 200
        else:
            log.info(f"Result: clear (top class {top_idx}, conf {top_conf:.2%})")
            return "clear", 200

    except Exception as e:
        log.error(f"Classification error: {e}")
        return "error", 500


@app.route("/health", methods=["GET"])
def health():
    return "ITT569 server running", 200


if __name__ == "__main__":
    log.info(f"Saving captures to: {SAVE_FOLDER}")
    log.info("Starting server on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)