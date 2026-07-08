# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- `requirements.txt` — pinned dependency versions
- `.gitignore` — excludes face encodings, database, venv, `.claude/`, `.DS_Store`
- `LICENSE` — MIT
- `CONTRIBUTING.md` — dev setup for macOS and Linux/Pi, architecture reference, privacy guidelines
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `CHANGELOG.md` — this file
- Improved `README.md` — database schema, systemd service template, multi-gate deployment guide

---

## [1.0.0] — Initial release

### Added

**`attendance_tracker.py`**
- Real-time face recognition via webcam using `face_recognition` (dlib HOG model)
- Automatic entry logging on first detection per session
- Automatic exit logging after `PRESENCE_TIMEOUT` seconds of absence
- Flush all open sessions on clean exit (Q key)
- Face registration CLI: `--add-face "Name" photo.jpg` saves `.npy` encoding
- Attendance report CLI: `--report [YYYY-MM-DD]` prints per-person session table with totals
- SQLite database with `events` (raw log) and `sessions` (calculated durations) tables
- Configurable constants: `PRESENCE_TIMEOUT`, `DETECTION_THRESHOLD`, `FRAME_SKIP`, `CAMERA_INDEX`, `DISPLAY_SCALE`
- Bounding boxes: green for known faces, red for unknowns; confidence percentage overlay
- HUD overlay showing current occupancy count

**`dashboard.py`**
- Live terminal dashboard using `rich.live.Live` for flicker-free updates
- "IN OFFICE" panel: person, arrival time, elapsed time — refreshes every 3 seconds
- "TODAY'S SESSIONS" panel: full session history with entry, exit, and duration
- Graceful exit on Ctrl-C
