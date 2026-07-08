# Image Recognition — Office Attendance Tracker

Automated office attendance tracking using real-time face recognition. Logs entry and exit times for each person via a webcam, stores sessions in a local SQLite database, and displays a live terminal dashboard.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-blue) ![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Raspberry%20Pi-lightgrey)

> **Privacy note:** All face encodings and attendance data are stored locally. Nothing is sent to any external server.

---

## Features

- **Real-time face recognition** via webcam — known faces boxed in green, unknowns in red
- **Automatic entry / exit logging** — first detection logs entry; absence beyond a configurable timeout logs exit
- **SQLite storage** — lightweight, zero-config, single-file database
- **Live terminal dashboard** — refreshes every 3 seconds showing who's in and today's session history
- **CLI attendance reports** — per-person totals for any date
- **Raspberry Pi ready** — HOG model runs at 6–8 fps on Pi 5; headless mode supported

---

## How it works

```
Camera frame
    │
    ▼
face_recognition detects faces (HOG model)
    │
    ▼
Compare encoding against known_faces/*.npy
    │
    ├── Match → log ENTRY on first sight / update last_seen on subsequent frames
    └── No match → red bounding box, no log

Background timeout loop
    └── last_seen > PRESENCE_TIMEOUT → log EXIT + close session with duration
```

### Entry / exit state machine

| Trigger | Action |
|---------|--------|
| Face first detected (not in `present` dict) | `entry` event + open session |
| Face keeps appearing | Update `last_seen` timestamp |
| Face absent for `PRESENCE_TIMEOUT` seconds | `exit` event + close session with duration |
| Tracker exits (Q pressed) | Flush all open sessions with current time |

---

## Quick start

### 1. Install dependencies

**macOS** (dlib requires cmake):
```bash
brew install cmake
pip install -r requirements.txt
```

**Linux / Raspberry Pi:**
```bash
sudo apt-get install -y cmake libboost-all-dev
pip install -r requirements.txt
```

### 2. Register faces

Take a clear, well-lit photo of each person (face visible, no sunglasses, frontal angle):
```bash
python attendance_tracker.py --add-face "Alice Smith" alice.jpg
python attendance_tracker.py --add-face "Bob Jones"   bob.jpg
```
Encodings are saved to `known_faces/` as `.npy` files — one per person.

### 3. Run the tracker

```bash
python attendance_tracker.py
```
A camera window opens. Press **Q** to quit and flush all open sessions.

### 4. Live dashboard (optional — second terminal)

```bash
python dashboard.py
```

### 5. Print a report

```bash
python attendance_tracker.py --report              # today
python attendance_tracker.py --report 2025-04-20  # specific date
```

---

## Configuration

Edit the constants at the top of `attendance_tracker.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `PRESENCE_TIMEOUT` | `30` | Seconds without detection before exit is logged |
| `DETECTION_THRESHOLD` | `0.5` | Face match tolerance — lower = stricter, fewer false positives |
| `FRAME_SKIP` | `5` | Run recognition every Nth frame — higher = less CPU usage |
| `CAMERA_INDEX` | `0` | `0` = built-in camera; `1` = first external USB camera |
| `DISPLAY_SCALE` | `0.75` | Scale factor for the display window |

---

## Project structure

```
image-recognition/
├── attendance_tracker.py   # Main tracker — face detection, logging, CLI
├── dashboard.py            # Live terminal dashboard (Rich UI)
├── requirements.txt        # Python dependencies
├── known_faces/            # Face encodings (*.npy per person) — gitignored
├── data/
│   └── attendance.db       # SQLite database — gitignored
└── README.md
```

---

## Database schema

```sql
-- Raw event log
CREATE TABLE events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    person  TEXT NOT NULL,
    event   TEXT NOT NULL,   -- 'entry' | 'exit'
    ts      TEXT NOT NULL    -- ISO timestamp
);

-- Calculated sessions with durations
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    person      TEXT NOT NULL,
    entry_ts    TEXT NOT NULL,
    exit_ts     TEXT,
    duration_s  INTEGER      -- seconds; NULL while session is open
);
```

---

## Raspberry Pi deployment

### Recommended hardware

| Component | Recommendation | Notes |
|-----------|---------------|-------|
| Board | Raspberry Pi 5 (4 GB) | Pi 4 works but slower; Pi 5 recommended |
| Camera | Camera Module 3 (wide angle) | Autofocus; good doorway coverage |
| Storage | 64 GB A2-rated microSD or USB SSD | SSD for high-frequency DB writes |
| Power | Official Pi 5 USB-C PSU (27 W) | Cheap PSUs cause random reboots |
| IR illuminator | Waveshare IR LED board or similar | Required for low-light / after-hours |

### Software adjustments for Pi

1. HOG model is already set — Pi cannot run the CNN model in real-time
2. Lower resolution: add `cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)` after `VideoCapture`
3. Increase `FRAME_SKIP` to `8`–`10`
4. Run headless: comment out the `cv2.imshow` and `cv2.waitKey` lines
5. Use `systemd` for auto-start on boot (see below)

### systemd service

Create `/etc/systemd/system/attendance.service`:
```ini
[Unit]
Description=Office Attendance Tracker
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/image-recognition/attendance_tracker.py
WorkingDirectory=/home/pi/image-recognition
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable attendance
sudo systemctl start attendance
```

### Performance expectations

| Hardware | Face detection FPS | Notes |
|----------|--------------------|-------|
| Mac M-series | ~25 fps | Excellent accuracy |
| Raspberry Pi 5 | ~6–8 fps | Good for single doorway |
| Raspberry Pi 4 | ~3–5 fps | Acceptable; increase FRAME_SKIP |

### Multi-gate deployment

- Run one `attendance_tracker.py` instance per camera (add `--gate entrance` argument to differentiate)
- All instances write to the same SQLite file, or switch to PostgreSQL for multi-process safety
- Use an MQTT broker (Mosquitto) to centralise events from multiple Pi nodes

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup and guidelines.

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT — see [LICENSE](LICENSE).
