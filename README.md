# ITT569 — Monkey Intruder Detection (Mini Project)

Short summary of the repository contents, how to set it up, and how to run the system (backend, frontend, and ESP32 firmware).

## Overview

- Backend: `server.py` — Flask server that runs a YOLOv8 model to classify incoming JPEG frames, saves captures to `captures/`, and logs detections to `detection_log.csv`.
- Frontend: `frontend/` — React + Vite dashboard that queries the backend API for stats, logs, and images.
- Firmware: `esp32s3_firmware/` — ESP32-S3 firmware that captures frames, sends them to the server `/classify` endpoint, and drives PIR/servo/LED/buzzer peripherals.

## Quick Start (summary)

Prerequisites:

- Python 3.11+ (recommended)
- Node.js + npm for the frontend
- An appropriate YOLOv8 `best.pt` model file (see below)

1) Backend

Install Python dependencies (recommended):

```bash
pip install -r requirements.txt
```

If you prefer to install individually, the server requires at minimum: `flask`, `flask-cors`, `ultralytics`, `pillow`, `requests`, and `python-dotenv`.

Configure Telegram (optional):

- Create a bot with @BotFather and obtain `TELEGRAM_TOKEN`.
- Obtain your chat id (use @userinfobot or `/getUpdates`).
- Provide values via environment variables or a `.env` file in the project root:

```
TELEGRAM_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Place the YOLO model:

- The server will look for the model using `MODEL_CANDIDATES` in `server.py`. Best practice: put your `best.pt` in `models/best.pt` or update `MODEL_CANDIDATES` / `MODEL_PATH` in `server.py`.

Run the server (from project root):

```bash
python server.py
```

Server endpoints (useful):

- `POST /classify` — Accepts raw JPEG bytes (ESP32 firmware uses this). Returns `monkey` or `clear`.
- `GET /health` — Basic health check.
- `GET /api/stats` — JSON stats from `detection_log.csv`.
- `GET /api/logs` — Full CSV logs as JSON.
- `GET /api/images/<filename>` — Serves saved capture images from `captures/`.
- `GET /test_telegram` and `GET /test_telegram_photo` — helpers to validate Telegram integration.

2) Frontend

Install and run:

```bash
cd frontend
npm install
npm run dev
```

By default the frontend expects the API at `http://127.0.0.1:5000/api`. Update `API_BASE` in `frontend/src/App.tsx` if your server runs on a different host/IP.

3) ESP32 Firmware

- Edit `esp32s3_firmware/config.h` and replace placeholders with your WiFi and server details. Keep these values as placeholders in repo copies; never commit secrets.

  - `WIFI_SSID` — your WiFi SSID
  - `WIFI_PASSWORD` — WiFi password
  - `SERVER_URL` — e.g. `http://<laptop_local_ip>:5000/classify`

- Build & flash using the Arduino IDE or PlatformIO as appropriate for your board.

Wiring (prototype summary):

- PIR sensor: VCC → 3.3V, GND → GND, OUT → GPIO 13 (or `PIN_PIR` in firmware)
- Servo: signal → `PIN_SERVO` (see sketch), power 3.3V (prototype)
- Buzzer: `PIN_BUZZER`
- LEDs: `PIN_LED_GREEN`, `PIN_LED_YELLOW`, `PIN_LED_RED` with current-limiting resistors

The repository previously included `SETUP_INSTRUCTIONS.txt`; it has been removed because it became outdated. The wiring summary above and troubleshooting notes are current — ask me if you want the full original file restored.

New helper files added:

- `.env.example` — example environment variables for `server.py` (copy to `.env` and fill locally).
- `scripts/install_model.py` — helper to copy a local `best.pt` into `models/best.pt` used by `server.py`.

## Configuration & Notes

- The backend reads optional `.env` variables (if present) and also supports setting `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` via environment variables.
- Firmware configuration should use placeholders in `esp32s3_firmware/config.h` (commit placeholders only). Replace locally before flashing.
- The server looks for a YOLO model; if not found it will raise `FileNotFoundError` with a suggestion about where to put `best.pt`.

- A `.gitignore` is included to prevent accidental commits of secrets and large artifacts: it ignores `.env` files, `models/best.pt`, `captures/`, and `detection_log.csv`.

## Troubleshooting

- If the camera fails to initialise on the ESP32, open the Serial Monitor at 115200 and inspect the printed error code. Boards differ in FPC mappings.
- If the server returns `error` on `/classify`, check `server.py` logs for exceptions and make sure the `best.pt` model path is correct.
- If Telegram alerts fail, verify that the bot can message the chat id and the token/chat id are correct. Use `/test_telegram` to verify.

## Data & Logs

- Captured images are stored in `captures/` (configured by `BASE_FOLDER` in `server.py`).
- A CSV log is kept at `detection_log.csv` in the project root. The server will create a fallback CSV inside `captures/` if the primary path is unavailable.

## Known Limitations

- Prototype hardware uses 3.3V for servo power (weaker than rated voltage).
- The provided YOLO model is expected to be a custom-trained `best.pt`. Off-the-shelf ImageNet models are not suitable.
- Adjust confidence thresholds in `server.py` inference call or pre/post-process if you change model/labels.

## Where to edit (quick reference)

- Backend server: `server.py`
- Frontend: `frontend/src` (start in `frontend/src/App.tsx`)
- Firmware config: `esp32s3_firmware/config.h`

---

If you'd like, I can:

- add a `.env.example` with the environment variables used by `server.py`;
- add a short script to upload a local `best.pt` into the expected model folder;
- or run the server locally and verify the endpoints from this environment (if you want that, tell me what to run).

Please tell me if you want any sections expanded or any values changed in this README.
