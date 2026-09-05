"""
RailBlock AI - Database Setup

Section Focus: Delhi – Ghaziabad

This database supports:

1. Railway maintenance tasks
2. Operational inputs provided for each task
3. Algorithm-generated Criticality, Urgency and Impact scores
4. Train schedules
5. Resource availability
6. Maintenance block proposals
7. Approval workflow
"""

import sqlite3
from pathlib import Path


# ============================================================
# DATABASE PATH
# ============================================================

# Database is stored inside the project's data folder.

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "railblock.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_conn():
    """
    Create and return a SQLite database connection.
    """

    # Create data folder if it does not exist.

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30
    )

    # Allows accessing columns using:
    #
    # row["column_name"]
    #
    # instead of:
    #
    # row[0]

    conn.row_factory = sqlite3.Row

    # Enable foreign key relationships.

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    """
    Create all database tables.

    IMPORTANT:

    This function currently deletes existing tables
    before creating new ones.

    This is suitable for an SIH prototype because
    it ensures the database schema is always clean.

    In production, migrations should be used instead.
    """

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = get_conn()

    c = conn.cursor()

    # ========================================================
    # DROP EXISTING TABLES
    # ========================================================

    # Child tables must be deleted first because
    # they depend on parent tables.

    c.executescript(
        """
        
        DROP TABLE IF EXISTS approvals;

        DROP TABLE IF EXISTS block_assignments;

        DROP TABLE IF EXISTS proposed_blocks;

        DROP TABLE IF EXISTS resource_availability;

        DROP TABLE IF EXISTS resources;

        DROP TABLE IF EXISTS tasks;

        DROP TABLE IF EXISTS train_schedule;

        DROP TABLE IF EXISTS sections;

        DROP TABLE IF EXISTS users;

        """
    )

    # ========================================================
    # CREATE TABLES
    # ========================================================

    c.executescript(
        """

        ------------------------------------------------------
        -- USERS
        ------------------------------------------------------

        CREATE TABLE users (

            id INTEGER PRIMARY KEY,

            name TEXT NOT NULL,

            role TEXT NOT NULL,

            department TEXT,

            initials TEXT,

            zone TEXT

        );


        ------------------------------------------------------
        -- RAILWAY SECTIONS
        ------------------------------------------------------

        CREATE TABLE sections (

            id INTEGER PRIMARY KEY,

            name TEXT NOT NULL UNIQUE,

            corridor TEXT,

            length_km REAL

        );


        ------------------------------------------------------
        -- TRAIN SCHEDULE
        ------------------------------------------------------

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

            FOREIGN KEY (section_id)

                REFERENCES sections(id)

        );


        ------------------------------------------------------
        -- MAINTENANCE TASKS
        ------------------------------------------------------

        CREATE TABLE tasks (

            id INTEGER PRIMARY KEY,

            --------------------------------------------------
            -- BASIC TASK INFORMATION
            --------------------------------------------------

            task_code TEXT UNIQUE,

            description TEXT,

            department TEXT,

            section_id INTEGER,


            --------------------------------------------------
            -- INPUTS FOR CRITICALITY CALCULATION
            --------------------------------------------------

            -- How severe is the detected fault?

            fault_severity REAL DEFAULT 0,

            -- Safety risk created by the fault

            safety_risk REAL DEFAULT 0,

            -- Importance of the railway asset

            asset_importance REAL DEFAULT 0,


            --------------------------------------------------
            -- INPUTS FOR URGENCY CALCULATION
            --------------------------------------------------

            -- How quickly the condition may deteriorate

            deterioration_rate REAL DEFAULT 0,

            -- Time pressure for completing the task

            response_deadline REAL DEFAULT 0,

            -- Whether delay increases safety concerns

            safety_escalation REAL DEFAULT 0,


            --------------------------------------------------
            -- INPUTS FOR IMPACT CALCULATION
            --------------------------------------------------

            -- Number / importance of trains affected

            trains_affected REAL DEFAULT 0,

            -- Importance of the railway route

            route_importance REAL DEFAULT 0,

            -- Expected operational disruption

            operational_disruption REAL DEFAULT 0,


            --------------------------------------------------
            -- ALGORITHM GENERATED SCORES
            --------------------------------------------------

            -- These values can be calculated by ai_engine.py

            criticality REAL DEFAULT 0,

            urgency REAL DEFAULT 0,

            impact REAL DEFAULT 0,


            --------------------------------------------------
            -- TASK REQUIREMENTS
            --------------------------------------------------

            -- Estimated work duration

            est_hours REAL,


            -- Number of days task is overdue

            overdue_days INTEGER DEFAULT 0,


            -- Required maintenance workers

            required_workers INTEGER DEFAULT 4,


            --------------------------------------------------
            -- SPECIAL RESOURCE REQUIREMENTS
            --------------------------------------------------

            requires_crane INTEGER DEFAULT 0,

            requires_tower_wagon INTEGER DEFAULT 0,

            requires_welding INTEGER DEFAULT 0,


            --------------------------------------------------
            -- TASK STATUS
            --------------------------------------------------

            status TEXT DEFAULT 'pending',


            --------------------------------------------------
            -- FOREIGN KEY
            --------------------------------------------------

            FOREIGN KEY (section_id)

                REFERENCES sections(id)

        );


        ------------------------------------------------------
        -- RESOURCES
        ------------------------------------------------------

        CREATE TABLE resources (

            id INTEGER PRIMARY KEY,

            name TEXT NOT NULL,

            resource_type TEXT NOT NULL,

            department TEXT,

            skill TEXT,

            total_count INTEGER DEFAULT 1

        );


        ------------------------------------------------------
        -- RESOURCE AVAILABILITY
        ------------------------------------------------------

        CREATE TABLE resource_availability (

            id INTEGER PRIMARY KEY,

            resource_id INTEGER NOT NULL,

            day_of_week TEXT,

            shift TEXT,

            available_count INTEGER,

            FOREIGN KEY (resource_id)

                REFERENCES resources(id)

        );


        ------------------------------------------------------
        -- PROPOSED MAINTENANCE BLOCKS
        ------------------------------------------------------

        CREATE TABLE proposed_blocks (

            id INTEGER PRIMARY KEY,

            block_code TEXT UNIQUE,

            section_id INTEGER,

            day_of_week TEXT,

            start_time TEXT,

            end_time TEXT,

            duration_hours REAL,

            status TEXT DEFAULT 'proposed',

            --------------------------------------------------
            -- ALGORITHM SCORE
            --------------------------------------------------

            ai_score REAL,

            --------------------------------------------------
            -- RESOURCE STATUS
            --------------------------------------------------

            resource_status TEXT,

            resource_notes TEXT,

            --------------------------------------------------
            -- TIMESTAMP
            --------------------------------------------------

            created_at TEXT

                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (section_id)

                REFERENCES sections(id)

        );


        ------------------------------------------------------
        -- BLOCK ASSIGNMENTS
        ------------------------------------------------------

        CREATE TABLE block_assignments (

            id INTEGER PRIMARY KEY,

            block_id INTEGER,

            task_id INTEGER,

            assigned_role TEXT,

            resource_id INTEGER,


            FOREIGN KEY (block_id)

                REFERENCES proposed_blocks(id),


            FOREIGN KEY (task_id)

                REFERENCES tasks(id),


            FOREIGN KEY (resource_id)

                REFERENCES resources(id)

        );


        ------------------------------------------------------
        -- APPROVALS
        ------------------------------------------------------

        CREATE TABLE approvals (

            id INTEGER PRIMARY KEY,

            block_id INTEGER,

            officer_id INTEGER,

            decision TEXT,

            comment TEXT,

            decided_at TEXT

                DEFAULT CURRENT_TIMESTAMP,


            FOREIGN KEY (block_id)

                REFERENCES proposed_blocks(id),


            FOREIGN KEY (officer_id)

                REFERENCES users(id)

        );

        """
    )

    # ========================================================
    # SAVE CHANGES
    # ========================================================

    conn.commit()

    conn.close()

    print(
        "Database initialized successfully:"
    )

    print(
        DB_PATH
    )


# ============================================================
# RUN DATABASE INITIALIZATION DIRECTLY
# ============================================================

if __name__ == "__main__":

    init_db()
