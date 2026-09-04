"""
RailBlock AI - FastAPI Backend
Delhi–Ghaziabad | Full features
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from database import get_conn, init_db
from seed import seed
from ai_engine import (
    list_tasks_with_priority,
    find_block_gaps,
    generate_block_proposals,
    save_proposals,
    whatif_delay,
    whatif_weather,
    check_resources,
)

app = FastAPI(title="RailBlock AI", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


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
    weather: str  # rain, heavy_rain, fog, heat, storm


@app.on_event("startup")
def startup():
    try:
        conn = get_conn()
        conn.execute("SELECT 1 FROM tasks LIMIT 1")
        conn.close()
    except Exception:
        try:
            seed()
        except Exception as e:
            print("WARNING: could not seed DB on startup:", e)


@app.get("/api/health")
def health():
    return {"status": "ok", "section": "Delhi–Ghaziabad"}


@app.get("/api/users")
def users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    # Return designation only (no personal names)
    out = []
    for r in rows:
        d = dict(r)
        d["name"] = d.get("role") or d.get("name")
        out.append(d)
    return out


@app.get("/api/tasks")
def tasks():
    return list_tasks_with_priority()


@app.get("/api/schedule")
def schedule(day: str = "Mon"):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT train_no, train_name, direction, day_of_week, departure_time, arrival_time, train_type
        FROM train_schedule WHERE section_id = 1 AND day_of_week = ?
        ORDER BY departure_time
        """,
        (day,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/gaps")
def gaps(day: str = "Mon"):
    return find_block_gaps(1, day)


@app.post("/api/optimize")
def optimize():
    proposals = generate_block_proposals(1)
    save_proposals(proposals)
    # serialize tasks for JSON
    out = []
    for p in proposals:
        item = {k: v for k, v in p.items() if k != "tasks"}
        item["tasks"] = [
            {
                "task_code": t["task_code"],
                "description": t["description"],
                "department": t["department"],
                "ai_score": t["ai_score"],
                "priority": t["priority"],
                "est_hours": t["est_hours"],
            }
            for t in p["tasks"]
        ]
        item["role_assignments"] = p["role_assignments"]
        item["resource_check"] = p["resource_check"]
        out.append(item)
    return {"count": len(out), "blocks": out}


@app.get("/api/blocks")
def blocks(status: Optional[str] = None):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM proposed_blocks WHERE status = ? ORDER BY day_of_week, start_time",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM proposed_blocks ORDER BY day_of_week, start_time"
        ).fetchall()
    result = []
    for r in rows:
        b = dict(r)
        tasks = conn.execute(
            """
            SELECT t.task_code, t.description, t.department, ba.assigned_role
            FROM block_assignments ba JOIN tasks t ON t.id = ba.task_id
            WHERE ba.block_id = ?
            """,
            (b["id"],),
        ).fetchall()
        b["tasks"] = [dict(t) for t in tasks]
        result.append(b)
    conn.close()
    return result


@app.post("/api/approve")
def approve(body: ApprovalIn):
    conn = get_conn()
    block = conn.execute(
        "SELECT id, status FROM proposed_blocks WHERE block_code = ?",
        (body.block_code,),
    ).fetchone()
    if not block:
        conn.close()
        raise HTTPException(404, "Block not found")
    if body.decision not in ("approved", "rejected", "modify"):
        conn.close()
        raise HTTPException(400, "decision must be approved|rejected|modify")

    conn.execute(
        "UPDATE proposed_blocks SET status = ? WHERE id = ?",
        (body.decision if body.decision != "modify" else "modify_requested", block["id"]),
    )
    conn.execute(
        "INSERT INTO approvals (block_id, officer_id, decision, comment) VALUES (?,?,?,?)",
        (block["id"], body.officer_id, body.decision, body.comment),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "block_code": body.block_code, "decision": body.decision}


@app.post("/api/whatif/delay")
def api_whatif_delay(body: WhatIfDelayIn):
    return whatif_delay(body.block_code, body.delay_hours)


@app.post("/api/whatif/weather")
def api_whatif_weather(body: WhatIfWeatherIn):
    return whatif_weather(body.block_code, body.weather)


@app.get("/api/resources")
def resources(day: str = "Mon"):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT r.name, r.resource_type, r.department, ra.available_count, ra.day_of_week
        FROM resources r
        JOIN resource_availability ra ON ra.resource_id = r.id
        WHERE ra.day_of_week = ?
        """,
        (day,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Serve frontend
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND / "index.html")
