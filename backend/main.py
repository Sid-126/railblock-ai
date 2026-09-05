"""
RailBlock AI - FastAPI Backend
Delhi–Ghaziabad | Full Features
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import get_conn
from seed import seed

from ai_engine import (
    list_tasks_with_priority,
    find_block_gaps,
    generate_block_proposals,
    save_proposals,
    whatif_delay,
    whatif_weather,
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="RailBlock AI",
    version="2.0",
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# FRONTEND PATH
# ============================================================

FRONTEND = (
    Path(__file__).resolve().parent.parent / "frontend"
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ApprovalIn(BaseModel):
    block_code: str
    officer_id: int = 1
    decision: str  # approved | rejected | modify
    comment: str = ""


class WhatIfDelayIn(BaseModel):
    block_code: str
    delay_hours: float = 2.0


class WhatIfWeatherIn(BaseModel):
    block_code: str
    weather: str


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    """
    Check whether the database is available.

    If the database or tables do not exist,
    initialize and seed the database.
    """

    try:
        conn = get_conn()

        conn.execute(
            "SELECT 1 FROM tasks LIMIT 1"
        )

        conn.close()

        print("Database ready.")

    except Exception:

        print(
            "Database not initialized. "
            "Creating and seeding database..."
        )

        try:
            seed()

            print(
                "Database initialized successfully."
            )

        except Exception as e:

            print(
                "WARNING: Could not seed database:",
                e
            )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "section": "Delhi–Ghaziabad",
        "system": "RailBlock AI",
    }


# ============================================================
# USERS / OFFICERS
# ============================================================

@app.get("/api/users")
def users():

    conn = get_conn()

    rows = conn.execute(
        "SELECT * FROM users"
    ).fetchall()

    conn.close()

    out = []

    for row in rows:

        user = dict(row)

        # Return designation instead of personal name
        user["name"] = (
            user.get("role")
            or user.get("name")
        )

        out.append(user)

    return out


# ============================================================
# TASKS + AI PRIORITY SCORING
# ============================================================

@app.get("/api/tasks")
def tasks():
    """
    Return all pending tasks.

    The AI engine dynamically calculates:

    - Criticality
    - Urgency
    - Impact
    - Overdue Score
    - Final AI Priority Score

    Tasks are returned sorted by priority.
    """

    return list_tasks_with_priority()


# ============================================================
# TRAIN SCHEDULE
# ============================================================

@app.get("/api/schedule")
def schedule(day: str = "Mon"):

    conn = get_conn()

    rows = conn.execute(
        """
        SELECT
            train_no,
            train_name,
            direction,
            day_of_week,
            departure_time,
            arrival_time,
            train_type

        FROM train_schedule

        WHERE section_id = 1
        AND day_of_week = ?

        ORDER BY departure_time
        """,
        (day,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# AVAILABLE BLOCK GAPS
# ============================================================

@app.get("/api/gaps")
def gaps(day: str = "Mon"):
    """
    Find possible maintenance block gaps
    between train movements.
    """

    return find_block_gaps(
        section_id=1,
        day=day,
    )


# ============================================================
# AI BLOCK OPTIMIZATION
# ============================================================

@app.post("/api/optimize")
def optimize():
    """
    Generate maintenance block proposals.

    Workflow:

    Tasks
        ↓
    AI Priority Calculation
        ↓
    Sort Tasks
        ↓
    Find Train Gaps
        ↓
    Select Tasks
        ↓
    Check Resources
        ↓
    Generate Block Proposals
    """

    proposals = generate_block_proposals(
        section_id=1
    )

    # Save generated proposals
    save_proposals(proposals)

    # Convert output into JSON-safe format
    out = []

    for proposal in proposals:

        # Copy everything except raw task objects
        item = {
            key: value
            for key, value in proposal.items()
            if key != "tasks"
        }

        # Serialize tasks
        item["tasks"] = [

            {
                "task_code": task["task_code"],
                "description": task["description"],
                "department": task["department"],

                # AI calculated priority
                "ai_score": task["ai_score"],

                # Priority label
                "priority": task["priority"],

                "est_hours": task["est_hours"],

                # Component scores
                "criticality": task.get(
                    "criticality"
                ),

                "urgency": task.get(
                    "urgency"
                ),

                "impact": task.get(
                    "impact"
                ),

                "overdue_score": task.get(
                    "overdue_score"
                ),
            }

            for task in proposal["tasks"]

        ]

        # Resource allocation information
        item["role_assignments"] = (
            proposal.get(
                "role_assignments",
                []
            )
        )

        item["resource_check"] = (
            proposal.get(
                "resource_check",
                {}
            )
        )

        out.append(item)

    return {

        "count": len(out),

        "blocks": out,

    }


# ============================================================
# GET PROPOSED BLOCKS
# ============================================================

@app.get("/api/blocks")
def blocks(
    status: Optional[str] = None
):

    conn = get_conn()

    if status:

        rows = conn.execute(
            """
            SELECT *

            FROM proposed_blocks

            WHERE status = ?

            ORDER BY
                day_of_week,
                start_time
            """,
            (status,),
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *

            FROM proposed_blocks

            ORDER BY
                day_of_week,
                start_time
            """
        ).fetchall()

    result = []

    for row in rows:

        block = dict(row)

        # Get tasks assigned to this block
        task_rows = conn.execute(
            """
            SELECT
                t.task_code,
                t.description,
                t.department,
                ba.assigned_role

            FROM block_assignments ba

            JOIN tasks t
            ON t.id = ba.task_id

            WHERE ba.block_id = ?
            """,
            (block["id"],),
        ).fetchall()

        block["tasks"] = [

            dict(task)

            for task in task_rows

        ]

        result.append(block)

    conn.close()

    return result


# ============================================================
# APPROVE / REJECT BLOCK
# ============================================================

@app.post("/api/approve")
def approve(
    body: ApprovalIn
):

    conn = get_conn()

    block = conn.execute(
        """
        SELECT id, status

        FROM proposed_blocks

        WHERE block_code = ?
        """,
        (body.block_code,),
    ).fetchone()

    if not block:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Block not found",
        )

    # Validate decision
    if body.decision not in (

        "approved",

        "rejected",

        "modify",

    ):

        conn.close()

        raise HTTPException(
            status_code=400,
            detail=(
                "decision must be "
                "approved|rejected|modify"
            ),
        )

    # Convert modify into database status
    new_status = (

        body.decision

        if body.decision != "modify"

        else "modify_requested"

    )

    # Update block status
    conn.execute(
        """
        UPDATE proposed_blocks

        SET status = ?

        WHERE id = ?
        """,
        (
            new_status,
            block["id"],
        ),
    )

    # Record approval decision
    conn.execute(
        """
        INSERT INTO approvals (

            block_id,

            officer_id,

            decision,

            comment

        )

        VALUES (?,?,?,?)
        """,
        (
            block["id"],
            body.officer_id,
            body.decision,
            body.comment,
        ),
    )

    conn.commit()

    conn.close()

    return {

        "ok": True,

        "block_code": body.block_code,

        "decision": body.decision,

    }


# ============================================================
# WHAT-IF: DELAY SIMULATION
# ============================================================

@app.post("/api/whatif/delay")
def api_whatif_delay(
    body: WhatIfDelayIn
):

    return whatif_delay(

        body.block_code,

        body.delay_hours,

    )


# ============================================================
# WHAT-IF: WEATHER SIMULATION
# ============================================================

@app.post("/api/whatif/weather")
def api_whatif_weather(
    body: WhatIfWeatherIn
):

    return whatif_weather(

        body.block_code,

        body.weather,

    )


# ============================================================
# RESOURCE AVAILABILITY
# ============================================================

@app.get("/api/resources")
def resources(
    day: str = "Mon"
):

    conn = get_conn()

    rows = conn.execute(
        """
        SELECT

            r.name,

            r.resource_type,

            r.department,

            r.skill,

            ra.available_count,

            ra.day_of_week,

            ra.shift

        FROM resources r

        JOIN resource_availability ra

        ON ra.resource_id = r.id

        WHERE ra.day_of_week = ?
        """,
        (day,),
    ).fetchall()

    conn.close()

    return [

        dict(row)

        for row in rows

    ]


# ============================================================
# SERVE FRONTEND
# ============================================================

if FRONTEND.exists():

    app.mount(

        "/static",

        StaticFiles(
            directory=str(FRONTEND)
        ),

        name="static",

    )

    @app.get("/")
    def index():

        return FileResponse(

            FRONTEND / "index.html"

        )
