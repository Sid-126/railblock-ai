"""
RailBlock AI - Database setup (SQLite)
Section focus: Delhi – Ghaziabad
"""
import sqlite3
from pathlib import Path

# Cross-platform: store DB inside project /data folder (works on Windows & Linux)
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "railblock.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    DROP TABLE IF EXISTS approvals;
    DROP TABLE IF EXISTS block_assignments;
    DROP TABLE IF EXISTS proposed_blocks;
    DROP TABLE IF EXISTS resource_availability;
    DROP TABLE IF EXISTS resources;
    DROP TABLE IF EXISTS tasks;
    DROP TABLE IF EXISTS train_schedule;
    DROP TABLE IF EXISTS sections;
    DROP TABLE IF EXISTS users;

    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT,
        initials TEXT,
        zone TEXT
    );

    CREATE TABLE sections (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        corridor TEXT,
        length_km REAL
    );

    CREATE TABLE train_schedule (
        id INTEGER PRIMARY KEY,
        section_id INTEGER NOT NULL,
        train_no TEXT,
        train_name TEXT,
        direction TEXT,
        day_of_week TEXT,
        departure_time TEXT,
        arrival_time TEXT,
        train_type TEXT,
        FOREIGN KEY (section_id) REFERENCES sections(id)
    );

    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        task_code TEXT UNIQUE,
        description TEXT,
        department TEXT,
        section_id INTEGER,
        criticality REAL,
        urgency REAL,
        impact REAL,
        est_hours REAL,
        overdue_days INTEGER DEFAULT 0,
        required_workers INTEGER DEFAULT 4,
        requires_crane INTEGER DEFAULT 0,
        requires_tower_wagon INTEGER DEFAULT 0,
        requires_welding INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (section_id) REFERENCES sections(id)
    );

    CREATE TABLE resources (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        department TEXT,
        skill TEXT,
        total_count INTEGER DEFAULT 1
    );

    CREATE TABLE resource_availability (
        id INTEGER PRIMARY KEY,
        resource_id INTEGER NOT NULL,
        day_of_week TEXT,
        shift TEXT,
        available_count INTEGER,
        FOREIGN KEY (resource_id) REFERENCES resources(id)
    );

    CREATE TABLE proposed_blocks (
        id INTEGER PRIMARY KEY,
        block_code TEXT UNIQUE,
        section_id INTEGER,
        day_of_week TEXT,
        start_time TEXT,
        end_time TEXT,
        duration_hours REAL,
        status TEXT DEFAULT 'proposed',
        ai_score REAL,
        resource_status TEXT,
        resource_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (section_id) REFERENCES sections(id)
    );

    CREATE TABLE block_assignments (
        id INTEGER PRIMARY KEY,
        block_id INTEGER,
        task_id INTEGER,
        assigned_role TEXT,
        resource_id INTEGER,
        FOREIGN KEY (block_id) REFERENCES proposed_blocks(id),
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (resource_id) REFERENCES resources(id)
    );

    CREATE TABLE approvals (
        id INTEGER PRIMARY KEY,
        block_id INTEGER,
        officer_id INTEGER,
        decision TEXT,
        comment TEXT,
        decided_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (block_id) REFERENCES proposed_blocks(id),
        FOREIGN KEY (officer_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()
    print("Database initialized:", DB_PATH)
