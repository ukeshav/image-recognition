"""
Office Attendance Tracker - POC for Mac
Uses webcam + face recognition to log entry/exit times.

Install deps:
    pip install opencv-python face_recognition numpy

Usage:
    1. Add colleague photos:  python attendance_tracker.py --add-face "John Doe" john.jpg
    2. Run tracker:           python attendance_tracker.py
    3. View report:           python attendance_tracker.py --report
"""

import cv2
import face_recognition
import sqlite3
import numpy as np
import time
import argparse
import os
import sys
from datetime import datetime, date
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
KNOWN_FACES_DIR = Path("known_faces")
DB_PATH = Path("data/attendance.db")
CAMERA_INDEX = 0          # 0 = built-in Mac camera; try 1 for external
FRAME_SKIP = 5            # Process every Nth frame (performance)
PRESENCE_TIMEOUT = 30     # Seconds before someone is considered "exited"
DETECTION_THRESHOLD = 0.5 # Face match tolerance (lower = stricter)
DISPLAY_SCALE = 0.75      # Scale down display window
# ─────────────────────────────────────────────────────────────────────────────


def init_db():
    """Create SQLite tables if they don't exist."""
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            person    TEXT    NOT NULL,
            event     TEXT    NOT NULL,          -- 'entry' | 'exit'
            ts        TEXT    NOT NULL            -- ISO timestamp
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            person      TEXT    NOT NULL,
            entry_ts    TEXT    NOT NULL,
            exit_ts     TEXT,
            duration_s  INTEGER                  -- filled on exit
        );
    """)
    con.commit()
    con.close()


def log_event(person: str, event: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    ts = datetime.now().isoformat(timespec="seconds")

    cur.execute("INSERT INTO events (person, event, ts) VALUES (?, ?, ?)",
                (person, event, ts))

    if event == "entry":
        cur.execute("INSERT INTO sessions (person, entry_ts) VALUES (?, ?)",
                    (person, ts))
    elif event == "exit":
        # Close the most recent open session for this person
        cur.execute("""
            SELECT id, entry_ts FROM sessions
            WHERE person = ? AND exit_ts IS NULL
            ORDER BY id DESC LIMIT 1
        """, (person,))
        row = cur.fetchone()
        if row:
            session_id, entry_ts = row
            entry_dt = datetime.fromisoformat(entry_ts)
            exit_dt  = datetime.fromisoformat(ts)
            duration = int((exit_dt - entry_dt).total_seconds())
            cur.execute("""
                UPDATE sessions SET exit_ts=?, duration_s=? WHERE id=?
            """, (ts, duration, session_id))

    con.commit()
    con.close()
    print(f"[{ts}] {event.upper():5s} → {person}")


# ── Face registration ─────────────────────────────────────────────────────────

def add_face(name: str, image_path: str):
    """Register a new person from a photo."""
    KNOWN_FACES_DIR.mkdir(exist_ok=True)
    img = face_recognition.load_image_file(image_path)
    encs = face_recognition.face_encodings(img)
    if not encs:
        print(f"ERROR: No face found in {image_path}")
        sys.exit(1)
    dest = KNOWN_FACES_DIR / f"{name.replace(' ', '_')}.npy"
    np.save(dest, encs[0])
    print(f"✓ Registered face for '{name}' → {dest}")


def load_known_faces() -> tuple[list, list]:
    """Load all registered face encodings from disk."""
    names, encodings = [], []
    for fp in KNOWN_FACES_DIR.glob("*.npy"):
        names.append(fp.stem.replace("_", " "))
        encodings.append(np.load(fp))
    print(f"Loaded {len(names)} known face(s): {names}")
    return names, encodings


# ── Main tracker loop ─────────────────────────────────────────────────────────

def run_tracker():
    init_db()
    known_names, known_encodings = load_known_faces()

    if not known_names:
        print("No registered faces found. Add some with --add-face first.")
        sys.exit(0)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("ERROR: Could not open camera. Check CAMERA_INDEX.")
        sys.exit(1)

    # State tracking
    present: dict[str, float] = {}   # name → last_seen timestamp
    frame_count = 0

    print("\n📷  Tracker running — press Q to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)  # faster detection
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        detected_names = []

        # Only run recognition every Nth frame
        if frame_count % FRAME_SKIP == 0:
            locations  = face_recognition.face_locations(rgb, model="hog")
            encodings  = face_recognition.face_encodings(rgb, locations)

            for enc, loc in zip(encodings, locations):
                distances = face_recognition.face_distance(known_encodings, enc)
                best_idx  = int(np.argmin(distances)) if len(distances) else -1

                if best_idx >= 0 and distances[best_idx] < DETECTION_THRESHOLD:
                    name = known_names[best_idx]
                    conf = 1 - distances[best_idx]
                else:
                    name = "Unknown"
                    conf = 0.0

                detected_names.append(name)

                # Scale coords back to full frame
                top, right, bottom, left = [v * 2 for v in loc]
                color = (0, 220, 80) if name != "Unknown" else (0, 80, 220)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                label = f"{name} ({conf:.0%})" if name != "Unknown" else "Unknown"
                cv2.rectangle(frame, (left, bottom - 28), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 4, bottom - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

                # Entry event
                if name != "Unknown" and name not in present:
                    log_event(name, "entry")

                # Update last-seen
                if name != "Unknown":
                    present[name] = time.time()

        # Exit detection: anyone not seen recently
        now = time.time()
        for name in list(present):
            if now - present[name] > PRESENCE_TIMEOUT:
                log_event(name, "exit")
                del present[name]

        # HUD overlay
        overlay_text = [
            f"IN OFFICE ({len(present)}): {', '.join(present.keys()) or 'nobody'}",
            "Press Q to quit"
        ]
        for i, txt in enumerate(overlay_text):
            cv2.putText(frame, txt, (10, 28 + i * 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 100), 2)

        display = cv2.resize(frame, (0, 0), fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)
        cv2.imshow("Office Attendance Tracker", display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Log everyone out on quit
    for name in list(present):
        log_event(name, "exit")

    cap.release()
    cv2.destroyAllWindows()
    print("\nTracker stopped. All open sessions closed.")


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(target_date: str = None):
    """Print a human-readable attendance report."""
    init_db()
    day = target_date or date.today().isoformat()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print(f"\n{'═'*55}")
    print(f"  ATTENDANCE REPORT  —  {day}")
    print(f"{'═'*55}")

    cur.execute("""
        SELECT person,
               entry_ts,
               exit_ts,
               duration_s
        FROM sessions
        WHERE DATE(entry_ts) = ?
        ORDER BY entry_ts
    """, (day,))
    rows = cur.fetchall()

    if not rows:
        print("  No sessions found for this date.")
    else:
        fmt = "  {:<20} {:<10} {:<10} {}"
        print(fmt.format("Person", "Entry", "Exit", "Duration"))
        print("  " + "-"*51)
        for person, entry, exit_ts, dur in rows:
            entry_t = entry[11:19] if entry else "–"
            exit_t  = exit_ts[11:19] if exit_ts else "still in"
            if dur:
                h, rem = divmod(dur, 3600)
                m, s   = divmod(rem, 60)
                dur_str = f"{h}h {m}m {s}s"
            else:
                dur_str = "ongoing"
            print(fmt.format(person, entry_t, exit_t, dur_str))

    # Summary
    cur.execute("""
        SELECT person, SUM(duration_s)
        FROM sessions
        WHERE DATE(entry_ts) = ? AND duration_s IS NOT NULL
        GROUP BY person
    """, (day,))
    totals = cur.fetchall()
    if totals:
        print(f"\n  {'─'*51}")
        print("  TOTAL TIME IN OFFICE:")
        for person, total in sorted(totals, key=lambda x: -x[1]):
            h, rem = divmod(total, 3600)
            m, s   = divmod(rem, 60)
            print(f"    {person:<20} {h}h {m}m {s}s")

    print(f"{'═'*55}\n")
    con.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Office Attendance Tracker")
    parser.add_argument("--add-face", nargs=2, metavar=("NAME", "IMAGE"),
                        help="Register a face: --add-face 'John Doe' photo.jpg")
    parser.add_argument("--report", nargs="?", const=True, metavar="YYYY-MM-DD",
                        help="Print today's report (or pass a date)")
    args = parser.parse_args()

    if args.add_face:
        add_face(args.add_face[0], args.add_face[1])
    elif args.report:
        date_arg = args.report if isinstance(args.report, str) else None
        print_report(date_arg)
    else:
        run_tracker()
