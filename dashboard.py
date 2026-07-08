"""
Live Attendance Dashboard — terminal UI
Run alongside attendance_tracker.py to see who's in the office.

    python dashboard.py

Requires: pip install rich
"""

import sqlite3
import time
from datetime import date, datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.columns import Columns
from rich import box

DB_PATH = Path("data/attendance.db")
REFRESH_INTERVAL = 3  # seconds


def get_currently_in():
    """Return people who have an open session (no exit_ts)."""
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT person, entry_ts
        FROM sessions
        WHERE exit_ts IS NULL
        ORDER BY entry_ts
    """)
    rows = cur.fetchall()
    con.close()
    return rows


def get_today_sessions():
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT person, entry_ts, exit_ts, duration_s
        FROM sessions
        WHERE DATE(entry_ts) = ?
        ORDER BY entry_ts DESC
        LIMIT 30
    """, (date.today().isoformat(),))
    rows = cur.fetchall()
    con.close()
    return rows


def fmt_duration(seconds):
    if seconds is None:
        now = datetime.now()
        return "ongoing"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def time_since(entry_ts):
    entry = datetime.fromisoformat(entry_ts)
    elapsed = int((datetime.now() - entry).total_seconds())
    return fmt_duration(elapsed)


def build_display():
    console = Console()
    now_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

    # Currently inside
    in_office = get_currently_in()
    in_table = Table(box=box.ROUNDED, expand=True, border_style="green")
    in_table.add_column("👤  Person", style="bold white")
    in_table.add_column("🕐  Arrived", style="cyan")
    in_table.add_column("⏱  Time Inside", style="yellow")

    for person, entry_ts in in_office:
        in_table.add_row(
            person,
            entry_ts[11:19],
            time_since(entry_ts)
        )

    in_panel = Panel(
        in_table,
        title=f"[bold green]🟢  IN OFFICE  ({len(in_office)})[/bold green]",
        border_style="green"
    )

    # Today's history
    sessions = get_today_sessions()
    hist_table = Table(box=box.SIMPLE, expand=True, border_style="dim")
    hist_table.add_column("Person", style="white")
    hist_table.add_column("In", style="cyan")
    hist_table.add_column("Out", style="magenta")
    hist_table.add_column("Duration", style="yellow")

    for person, entry_ts, exit_ts, dur in sessions:
        hist_table.add_row(
            person,
            entry_ts[11:19],
            exit_ts[11:19] if exit_ts else "–",
            fmt_duration(dur)
        )

    hist_panel = Panel(
        hist_table,
        title="[bold blue]📋  TODAY'S SESSIONS[/bold blue]",
        border_style="blue"
    )

    header = Panel(
        f"[bold]Office Attendance POC[/bold]  ·  {now_str}  ·  Refresh: {REFRESH_INTERVAL}s",
        border_style="dim"
    )

    return header, in_panel, hist_panel


def main():
    console = Console()
    console.clear()

    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            try:
                header, in_panel, hist_panel = build_display()
                from rich.console import Group
                live.update(Group(header, in_panel, hist_panel))
                time.sleep(REFRESH_INTERVAL)
            except KeyboardInterrupt:
                break

    console.print("\n[dim]Dashboard closed.[/dim]")


if __name__ == "__main__":
    main()
