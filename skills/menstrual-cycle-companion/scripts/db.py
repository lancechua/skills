"""
SQLite data layer for the menstrual cycle companion skill.

Design notes:
- One database holds multiple profiles (e.g. a cycler and a
  supporting partner) so the household can share a single data file.
- Cycle prediction is derived from `period_starts`, not from daily_logs, so
  the source of truth for "when did a period begin" is always an explicit
  log entry rather than an inference from flow values.
- All dates are stored as ISO strings (YYYY-MM-DD) for simple lexical sort.
"""

import os
import sqlite3
from contextlib import contextmanager


def get_data_dir():
    return os.path.expanduser(
        os.environ.get("MCC_DATA_DIR", "~/.menstrual-cycle-companion")
    )


def get_db_path():
    return os.path.join(get_data_dir(), "data.db")


# Default values for module-level compatibility
DEFAULT_DATA_DIR = get_data_dir()
DB_PATH = get_db_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK(role IN ('cycler', 'partner')),
    -- bootstrap values, used only until >=2 real cycles are logged
    bootstrap_cycle_length INTEGER,
    bootstrap_period_length INTEGER,
    bootstrap_luteal_length INTEGER,
    linked_profile_id INTEGER REFERENCES profiles(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS period_starts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    start_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(profile_id, start_date)
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    log_date TEXT NOT NULL,
    flow TEXT CHECK(flow IN ('none', 'spotting', 'light', 'medium', 'heavy') OR flow IS NULL),
    pain INTEGER CHECK(pain BETWEEN 0 AND 10 OR pain IS NULL),
    symptoms TEXT,        -- comma-separated tags, e.g. "cramps,headache,bloating"
    mood TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(profile_id, log_date)
);

CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    event_type TEXT NOT NULL,   -- e.g. 'period_upcoming', 'fertile_window_upcoming'
    cycle_anchor_date TEXT NOT NULL, -- e.g. predicted period date or fertile start
    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(profile_id, event_type, cycle_anchor_date)
);
"""


@contextmanager
def get_conn(allow_create=False):
    db_path = get_db_path()
    data_dir = get_data_dir()
    if not allow_create and not os.path.exists(db_path):
        raise RuntimeError(
            f"Database not found at {db_path}. Please run setup first (e.g. `python cli.py init`)."
        )
    os.makedirs(data_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn(allow_create=True) as conn:
        conn.executescript(SCHEMA)


def add_profile(
    name,
    role,
    bootstrap_cycle_length=None,
    bootstrap_period_length=None,
    bootstrap_luteal_length=None,
    linked_profile_id=None,
):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO profiles (name, role, bootstrap_cycle_length,
                                     bootstrap_period_length, bootstrap_luteal_length,
                                     linked_profile_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name,
                role,
                bootstrap_cycle_length,
                bootstrap_period_length,
                bootstrap_luteal_length,
                linked_profile_id,
            ),
        )
        return cur.lastrowid


def get_profile(name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None


def list_profiles():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM profiles ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def update_bootstrap(
    name, cycle_length=None, period_length=None, luteal_length=None
):
    profile = get_profile(name)
    if not profile:
        raise ValueError(f"Profile {name!r} not found")
    with get_conn() as conn:
        conn.execute(
            """UPDATE profiles
               SET bootstrap_cycle_length = coalesce(?, bootstrap_cycle_length),
                   bootstrap_period_length = coalesce(?, bootstrap_period_length),
                   bootstrap_luteal_length = coalesce(?, bootstrap_luteal_length)
               WHERE name = ?""",
            (cycle_length, period_length, luteal_length, name),
        )


def log_period_start(profile_name, start_date, notes=None):
    profile = get_profile(profile_name)
    if not profile:
        raise ValueError(f"Profile {profile_name!r} not found")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO period_starts (profile_id, start_date, notes)
               VALUES (?, ?, ?)
               ON CONFLICT(profile_id, start_date) DO UPDATE SET notes = excluded.notes""",
            (profile["id"], start_date, notes),
        )


def get_period_starts(profile_name, limit=12):
    profile = get_profile(profile_name)
    if not profile:
        raise ValueError(f"Profile {profile_name!r} not found")
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM period_starts
               WHERE profile_id = ?
               ORDER BY start_date ASC""",
            (profile["id"],),
        ).fetchall()
        # return last `limit` in chronological order
        return [dict(r) for r in rows][-limit:]


def log_daily(
    profile_name,
    log_date,
    flow=None,
    pain=None,
    symptoms=None,
    mood=None,
    notes=None,
):
    profile = get_profile(profile_name)
    if not profile:
        raise ValueError(f"Profile {profile_name!r} not found")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO daily_logs (profile_id, log_date, flow, pain, symptoms, mood, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(profile_id, log_date) DO UPDATE SET
                   flow = coalesce(excluded.flow, flow),
                   pain = coalesce(excluded.pain, pain),
                   symptoms = coalesce(excluded.symptoms, symptoms),
                   mood = coalesce(excluded.mood, mood),
                   notes = coalesce(excluded.notes, notes)""",
            (profile["id"], log_date, flow, pain, symptoms, mood, notes),
        )


def get_daily_logs(profile_name, limit=30):
    profile = get_profile(profile_name)
    if not profile:
        raise ValueError(f"Profile {profile_name!r} not found")
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM daily_logs
               WHERE profile_id = ?
               ORDER BY log_date DESC
               LIMIT ?""",
            (profile["id"], limit),
        ).fetchall()
        return [dict(r) for r in rows]


def was_notified(profile_id, event_type, cycle_anchor_date):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT 1 FROM notification_log
               WHERE profile_id = ? AND event_type = ? AND cycle_anchor_date = ?""",
            (profile_id, event_type, cycle_anchor_date),
        ).fetchone()
        return row is not None


def record_notification(profile_id, event_type, cycle_anchor_date):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO notification_log
               (profile_id, event_type, cycle_anchor_date)
               VALUES (?, ?, ?)""",
            (profile_id, event_type, cycle_anchor_date),
        )
