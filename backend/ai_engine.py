"""
RailBlock AI Engine
- Priority scoring
- Train-schedule gap finder (Delhi–Ghaziabad)
- Resource & personnel check
- Role assignment
- Block proposal generation
- What-If (delay / weather)
"""
from database import get_conn
from datetime import datetime, timedelta


def time_to_min(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def min_to_time(m: int) -> str:
    m = m % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def compute_priority(task: dict) -> float:
    """AI priority score (can be replaced by ML model later)."""
    score = (
        0.40 * task["criticality"]
        + 0.30 * task["urgency"]
        + 0.20 * task["impact"]
        + 0.10 * min(100, task.get("overdue_days", 0) * 15)
    )
    return round(score, 1)


def get_priority_label(score: float) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def find_block_gaps(section_id: int = 1, day: str = "Mon", min_gap_minutes: int = 60):
    """
    Read train schedule and find free windows suitable for maintenance blocks.
    Returns list of gaps sorted by suitability (longer + off-peak preferred).
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT departure_time, arrival_time, train_no, train_name, train_type
        FROM train_schedule
        WHERE section_id = ? AND day_of_week = ?
        ORDER BY departure_time
        """,
        (section_id, day),
    ).fetchall()
    conn.close()

    if not rows:
        # Full day available if no trains
        return [{
            "start": "06:00",
            "end": "18:00",
            "duration_hours": 12.0,
            "suitability": 90,
            "reason": "No trains scheduled",
        }]

    occupied = []
    for r in rows:
        start = time_to_min(r["departure_time"])
        end = time_to_min(r["arrival_time"])
        if end < start:
            end += 24 * 60
        # Buffer 15 min before/after train
        occupied.append((max(0, start - 10), min(24 * 60, end + 10)))

    occupied.sort()
    merged = []
    for s, e in occupied:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append([s, e])

    gaps = []
    cursor = 5 * 60  # from 05:00
    day_end = 23 * 60 + 30

    for s, e in merged:
        if s - cursor >= min_gap_minutes:
            dur_h = (s - cursor) / 60
            mid = (cursor + s) / 2
            # Prefer mid-day 10-14 and night 21-24
            if 10 * 60 <= mid <= 14 * 60:
                suit = 85 + min(10, dur_h)
            elif mid >= 21 * 60 or mid <= 6 * 60:
                suit = 80 + min(10, dur_h)
            else:
                suit = 60 + min(15, dur_h)
            gaps.append({
                "start": min_to_time(cursor),
                "end": min_to_time(s),
                "duration_hours": round(dur_h, 1),
                "suitability": round(suit, 1),
                "reason": "Free window between trains",
            })
        cursor = max(cursor, e)

    if day_end - cursor >= min_gap_minutes:
        dur_h = (day_end - cursor) / 60
        gaps.append({
            "start": min_to_time(cursor),
            "end": min_to_time(day_end),
            "duration_hours": round(dur_h, 1),
            "suitability": 75,
            "reason": "Evening free window",
        })

    gaps.sort(key=lambda g: -g["suitability"])
    return gaps


def check_resources(day: str, tasks: list) -> dict:
    """
    Check whether workers, crane, tower wagon, welding are available
    for the given day and set of tasks.
    """
    conn = get_conn()
    need_workers = sum(t.get("required_workers", 4) for t in tasks)
    need_crane = any(t.get("requires_crane") for t in tasks)
    need_tw = any(t.get("requires_tower_wagon") for t in tasks)
    need_weld = any(t.get("requires_welding") for t in tasks)

    def avail(resource_id):
        row = conn.execute(
            """
            SELECT available_count FROM resource_availability
            WHERE resource_id = ? AND day_of_week = ? AND shift = 'day'
            """,
            (resource_id, day),
        ).fetchone()
        return row["available_count"] if row else 0

    # Aggregate workers: gangs 1-4
    workers_avail = avail(1) + avail(2) + avail(3) + avail(4)
    crane_avail = avail(5)
    tw_avail = avail(6)
    weld_avail = avail(7)
    sup_avail = avail(8)
    conn.close()

    details = []
    ok = True

    details.append({
        "item": "Workers (gangs)",
        "required": need_workers,
        "available": workers_avail,
        "status": "Available" if workers_avail >= need_workers else "Shortage",
    })
    if workers_avail < need_workers:
        ok = False

    details.append({
        "item": "Supervisor (JE/SSE)",
        "required": 1,
        "available": sup_avail,
        "status": "Available" if sup_avail >= 1 else "Shortage",
    })
    if sup_avail < 1:
        ok = False

    if need_crane:
        details.append({
            "item": "Rail Crane",
            "required": 1,
            "available": crane_avail,
            "status": "Available" if crane_avail >= 1 else "Not available",
        })
        if crane_avail < 1:
            ok = False

    if need_tw:
        details.append({
            "item": "Tower Wagon",
            "required": 1,
            "available": tw_avail,
            "status": "Available" if tw_avail >= 1 else "Not available",
        })
        if tw_avail < 1:
            ok = False

    if need_weld:
        details.append({
            "item": "Welding Unit",
            "required": 1,
            "available": weld_avail,
            "status": "Available" if weld_avail >= 1 else "Shortage",
        })
        if weld_avail < 1:
            ok = False

    notes = []
    for d in details:
        if d["status"] != "Available":
            notes.append(f"{d['item']}: need {d['required']}, have {d['available']}")

    return {
        "ok": ok,
        "details": details,
        "notes": "; ".join(notes) if notes else "All required resources available",
        "summary": "READY" if ok else "SHORTAGE",
    }


def assign_roles(tasks: list) -> list:
    """AI assigns roles based on department / task type."""
    assignments = []
    for t in tasks:
        dept = t["department"]
        if dept == "Engineering":
            roles = ["SSE/JE (P.Way)", "P.Way Gang", "Welder" if t.get("requires_welding") else None]
            if t.get("requires_crane"):
                roles.append("Crane Operator")
        elif dept == "S&T":
            roles = ["JE (Signal)", "Signal Maintainer"]
        elif dept == "Traction":
            roles = ["JE (TRD)", "TRD Gang"]
            if t.get("requires_tower_wagon"):
                roles.append("Tower Wagon Operator")
        else:
            roles = ["Supervisor"]
        roles = [r for r in roles if r]
        assignments.append({
            "task_code": t["task_code"],
            "description": t["description"],
            "department": dept,
            "roles": roles,
        })
    return assignments


def generate_block_proposals(section_id: int = 1, days: list = None):
    """
    Core AI: for each day, find best gaps from train schedule,
    pick high-priority tasks, check resources, assign roles,
    create proposed blocks.
    """
    if days is None:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    conn = get_conn()
    task_rows = conn.execute(
        "SELECT * FROM tasks WHERE section_id = ? AND status = 'pending'",
        (section_id,),
    ).fetchall()
    conn.close()

    tasks = [dict(r) for r in task_rows]
    for t in tasks:
        t["ai_score"] = compute_priority(t)
        t["priority"] = get_priority_label(t["ai_score"])
    tasks.sort(key=lambda x: -x["ai_score"])

    proposals = []
    used_task_ids = set()
    block_num = 1

    for day in days:
        gaps = find_block_gaps(section_id, day, min_gap_minutes=60)
        if not gaps:
            continue

        # Take top gap for this day
        for gap in gaps[:4]:
            remaining = [t for t in tasks if t["id"] not in used_task_ids]
            if not remaining:
                break

            selected = []
            hours_left = gap["duration_hours"]
            for t in remaining:
                if t["est_hours"] <= hours_left + 0.5:
                    selected.append(t)
                    hours_left -= t["est_hours"]
                    if hours_left < 1.0:
                        break
            if not selected:
                continue

            res = check_resources(day, selected)
            roles = assign_roles(selected)
            avg_score = sum(t["ai_score"] for t in selected) / len(selected)

            proposals.append({
                "block_code": f"BLK-DG-{block_num:03d}",
                "section": "Delhi–Ghaziabad",
                "day": day,
                "start_time": gap["start"],
                "end_time": gap["end"],
                "duration_hours": gap["duration_hours"],
                "gap_reason": gap["reason"],
                "suitability": gap["suitability"],
                "ai_score": round(avg_score, 1),
                "tasks": selected,
                "resource_check": res,
                "role_assignments": roles,
                "status": "proposed",
            })
            for t in selected:
                used_task_ids.add(t["id"])
            block_num += 1

    return proposals


def save_proposals(proposals: list):
    """Persist proposals to DB for officer approval."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM block_assignments")
    c.execute("DELETE FROM approvals")
    c.execute("DELETE FROM proposed_blocks")

    for p in proposals:
        c.execute(
            """
            INSERT INTO proposed_blocks
            (block_code, section_id, day_of_week, start_time, end_time, duration_hours,
             status, ai_score, resource_status, resource_notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                p["block_code"],
                1,
                p["day"],
                p["start_time"],
                p["end_time"],
                p["duration_hours"],
                "proposed",
                p["ai_score"],
                p["resource_check"]["summary"],
                p["resource_check"]["notes"],
            ),
        )
        block_id = c.lastrowid
        for t in p["tasks"]:
            c.execute(
                "INSERT INTO block_assignments (block_id, task_id, assigned_role) VALUES (?,?,?)",
                (block_id, t["id"], t["department"]),
            )
    conn.commit()
    conn.close()


def whatif_delay(block_code: str, delay_hours: float) -> dict:
    """What if this block work is delayed by X hours."""
    conn = get_conn()
    block = conn.execute(
        "SELECT * FROM proposed_blocks WHERE block_code = ?", (block_code,)
    ).fetchone()
    conn.close()
    if not block:
        return {"error": "Block not found"}

    base_avail = 94.2
    impact = delay_hours * 0.35
    if block["ai_score"] and block["ai_score"] >= 85:
        impact += 1.0
    new_avail = round(base_avail - impact, 1)

    return {
        "scenario": "delay",
        "block_code": block_code,
        "delay_hours": delay_hours,
        "original_window": f"{block['day_of_week']} {block['start_time']}–{block['end_time']}",
        "projected_availability": new_avail,
        "availability_drop": round(impact, 1),
        "effects": [
            f"Asset availability drops by ~{impact:.1f}%",
            "Downstream blocks may shift by half day or more",
            "Risk of train punctuality impact on Delhi–Ghaziabad",
            "Critical defects remain open longer" if (block["ai_score"] or 0) >= 85 else "Medium priority work deferred",
        ],
        "ai_suggestion": (
            f"Prefer re-slotting within next 24–48h using next best gap. "
            f"Resource status was: {block['resource_status']}."
        ),
    }


def whatif_weather(block_code: str, weather: str) -> dict:
    """What if weather changes: rain, fog, heat, storm."""
    weather = weather.lower()
    outdoor_risk = {
        "rain": ("High", "Track & OHE outdoor work unsafe; postpone ballast, OHE insulator, crane lifts"),
        "heavy_rain": ("Critical", "Stop all outdoor blocks; only indoor/relay room work possible"),
        "fog": ("Medium", "Signal sighting issues; avoid complex signalling tests at night"),
        "heat": ("Medium", "Limit continuous outdoor hours; schedule early morning only"),
        "storm": ("Critical", "Cancel block; secure OHE and track sites"),
    }
    level, msg = outdoor_risk.get(weather, ("Low", "No major restriction"))

    return {
        "scenario": "weather",
        "block_code": block_code,
        "weather": weather,
        "risk_level": level,
        "message": msg,
        "ai_actions": [
            "Re-evaluate outdoor Engineering and TRD tasks",
            "Keep S&T indoor tasks if safe",
            "Move crane-dependent work to next clear day",
            "Notify officer for approval of revised plan",
        ],
        "recommended": "Postpone" if level in ("High", "Critical") else "Proceed with caution",
    }


def list_tasks_with_priority():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tasks WHERE section_id = 1").fetchall()
    conn.close()
    out = []
    for r in rows:
        t = dict(r)
        t["ai_score"] = compute_priority(t)
        t["priority"] = get_priority_label(t["ai_score"])
        out.append(t)
    out.sort(key=lambda x: -x["ai_score"])
    return out
