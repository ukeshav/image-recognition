# Contributing to Image Recognition — Office Attendance Tracker

Thank you for your interest! This is a small, focused project and contributions of all sizes are welcome.

---

## Table of contents

- [Code of conduct](#code-of-conduct)
- [How to contribute](#how-to-contribute)
- [Development setup](#development-setup)
- [Project architecture](#project-architecture)
- [Submitting a pull request](#submitting-a-pull-request)
- [Reporting bugs](#reporting-bugs)
- [Privacy considerations](#privacy-considerations)

---

## Code of conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) code of conduct. By participating you agree to abide by its terms.

---

## How to contribute

- **Bug fixes** — open a PR with a clear description of the problem and fix
- **New features** — open an issue first to discuss before writing code
- **Documentation** — improvements to README, inline comments, or this guide are always welcome
- **Platform support** — tested on macOS and Raspberry Pi; Windows support is a known gap
- **Tests** — the project has no automated tests yet; adding them would be a great first contribution

---

## Development setup

### Prerequisites

- Python 3.10+
- `cmake` (required by `dlib`, which powers `face_recognition`)
- A webcam

### macOS

```bash
brew install cmake
git clone https://github.com/ukeshav/image-recognition.git
cd image-recognition
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Linux / Raspberry Pi

```bash
sudo apt-get install -y cmake libboost-all-dev
git clone https://github.com/ukeshav/image-recognition.git
cd image-recognition
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Register a test face and run

```bash
# Register yourself (or use any photo with a clear face)
python attendance_tracker.py --add-face "Test User" your_photo.jpg

# Run the tracker
python attendance_tracker.py

# In a second terminal — live dashboard
python dashboard.py

# Print today's report
python attendance_tracker.py --report
```

---

## Project architecture

```
attendance_tracker.py    Core: detection loop, event logging, CLI
dashboard.py             Terminal UI: reads DB, renders live tables via Rich
known_faces/             One *.npy file per registered person (gitignored)
data/attendance.db       SQLite database (gitignored)
```

### `attendance_tracker.py` internals

| Component | Description |
|-----------|-------------|
| `init_db()` | Creates `events` and `sessions` SQLite tables on first run |
| `add_face()` | Encodes a photo with `face_recognition` and saves as `.npy` |
| `load_known_faces()` | Loads all `.npy` files from `known_faces/` at startup |
| `run_tracker()` | Main loop: capture → resize → detect → match → log |
| `log_event()` | Writes entry/exit to `events`; opens/closes rows in `sessions` |
| `print_report()` | Queries `sessions` for a given date and prints a formatted table |

**Detection pipeline per frame:**

1. Resize frame to 50% for faster processing
2. Convert BGR → RGB (OpenCV vs face_recognition colour order)
3. Every `FRAME_SKIP` frames: run `face_locations` (HOG) + `face_encodings`
4. For each detected encoding: compute `face_distance` against all knowns; pick closest
5. If distance < `DETECTION_THRESHOLD` → matched; else → Unknown
6. Track in `present` dict; entry on first match, exit on timeout

### `dashboard.py` internals

- Queries `sessions WHERE exit_ts IS NULL` for current occupancy
- Queries `sessions WHERE DATE(entry_ts) = today` for history
- Uses `rich.live.Live` for flicker-free in-place terminal updates every 3 seconds

---

## Submitting a pull request

1. Fork the repo and create a branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make changes and commit with a clear message:
   ```bash
   git commit -m "feat: add --gate flag to tag events by camera location"
   ```
3. Push and open a PR against `main`
4. Describe what changed and why in the PR description

### Commit message style

Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|--------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Maintenance, deps, config |
| `refactor:` | Code change with no behaviour change |
| `perf:` | Performance improvement (e.g. frame processing) |

---

## Reporting bugs

Open a [GitHub issue](https://github.com/ukeshav/image-recognition/issues/new) and include:

- Python version and OS
- Hardware (Mac / Pi model / USB camera)
- Full error traceback
- Steps to reproduce

---

## Privacy considerations

This project processes biometric data (face encodings). When contributing:

- **Never commit face encodings** (`.npy` files) or database files — both are gitignored
- **Never add external API calls** that could transmit face data or personal info
- **Document any new data storage** clearly in the PR description
- If adding a network feature (e.g. MQTT), ensure it transmits only events (person name + timestamp), not raw encodings or images
