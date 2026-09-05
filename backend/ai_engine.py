```python
"""
RailBlock AI Engine

Features:
- Rule-based multi-criteria task priority scoring
- Train schedule gap detection
- Department-specific resource checking
- Role assignment
- Constraint-based heuristic block scheduling
- What-If delay simulation
- What-If weather simulation
"""

from database import get_conn


# ============================================================
# TIME HELPER FUNCTIONS
# ============================================================

def time_to_min(t: str) -> int:
    """Convert HH:MM time into total minutes."""

    h, m = map(int, t.split(":"))
    return h * 60 + m


def min_to_time(m: int) -> str:
    """Convert total minutes into HH:MM format."""

    m = m % (24 * 60)

    return f"{m // 60:02d}:{m % 60:02d}"


# ============================================================
# TASK SCORING ENGINE
# ============================================================
#
# This is a rule-based multi-criteria decision system.
#
# It calculates:
#
# 1. Criticality
# 2. Urgency
# 3. Impact
# 4. Overdue Score
# 5. Final Priority Score
#
# ============================================================


def map_score(value, mapping, default=0):
    """
    Convert a text category into a numerical score.
    """

    if value is None:
        return default

    return mapping.get(
        str(value).lower().strip(),
        default
    )


# ============================================================
# CRITICALITY CALCULATION
# ============================================================

def calculate_criticality(task: dict) -> float:
    """
    Criticality depends on:

    Fault Severity     = 40%
    Safety Risk        = 40%
    Asset Importance   = 20%
    """

    severity_scores = {
        "minor": 25,
        "moderate": 50,
        "major": 75,
        "severe": 90,
        "critical": 100,
    }

    safety_scores = {
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 100,
    }

    asset_scores = {
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 100,
    }

    fault_severity = map_score(
        task.get("fault_severity"),
        severity_scores
    )

    safety_risk = map_score(
        task.get("safety_risk"),
        safety_scores
    )

    asset_importance = map_score(
        task.get("asset_importance"),
        asset_scores
    )

    score = (
        0.40 * fault_severity
        + 0.40 * safety_risk
        + 0.20 * asset_importance
    )

    return round(score, 1)


# ============================================================
# URGENCY CALCULATION
# ============================================================

def calculate_urgency(task: dict) -> float:
    """
    Urgency depends on:

    Deterioration Rate = 35%
    Response Deadline  = 45%
    Safety Escalation  = 20%
    """

    deterioration_scores = {
        "slow": 25,
        "moderate": 50,
        "fast": 75,
        "rapid": 100,
    }

    deadline_scores = {
        "within_7_days": 25,
        "within_3_days": 50,
        "within_24_hours": 75,
        "immediate": 100,
    }

    escalation_scores = {
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 100,
    }

    deterioration_rate = map_score(
        task.get("deterioration_rate"),
        deterioration_scores
    )

    response_deadline = map_score(
        task.get("response_deadline"),
        deadline_scores
    )

    safety_escalation = map_score(
        task.get("safety_escalation"),
        escalation_scores
    )

    score = (
        0.35 * deterioration_rate
        + 0.45 * response_deadline
        + 0.20 * safety_escalation
    )

    return round(score, 1)


# ============================================================
# IMPACT CALCULATION
# ============================================================

def calculate_impact(task: dict) -> float:
    """
    Impact depends on:

    Trains Affected          = 40%
    Route Importance         = 30%
    Operational Disruption   = 30%
    """

    trains_affected = task.get(
        "trains_affected",
        0
    )

    if trains_affected >= 80:
        train_score = 100

    elif trains_affected >= 60:
        train_score = 75

    elif trains_affected >= 40:
        train_score = 50

    elif trains_affected >= 20:
        train_score = 25

    else:
        train_score = 10

    route_scores = {
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 100,
    }

    disruption_scores = {
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 100,
    }

    route_importance = map_score(
        task.get("route_importance"),
        route_scores
    )

    operational_disruption = map_score(
        task.get("operational_disruption"),
        disruption_scores
    )

    score = (
        0.40 * train_score
        + 0.30 * route_importance
        + 0.30 * operational_disruption
    )

    return round(score, 1)


# ============================================================
# OVERDUE SCORE
# ============================================================

def calculate_overdue_score(task: dict) -> float:
    """
    Every overdue day increases the score by 15.

    Maximum score = 100.
    """

    overdue_days = task.get(
        "overdue_days",
        0
    )

    score = min(
        100,
        overdue_days * 15
    )

    return round(score, 1)


# ============================================================
# FINAL PRIORITY CALCULATION
# ============================================================

def compute_priority(task: dict) -> float:
    """
    Final priority calculation:

    Criticality = 40%
    Urgency     = 30%
    Impact      = 20%
    Overdue     = 10%
    """

    criticality = calculate_criticality(task)

    urgency = calculate_urgency(task)

    impact = calculate_impact(task)

    overdue_score = calculate_overdue_score(task)

    # Store component scores for API/frontend explanation

    task["criticality"] = criticality

    task["urgency"] = urgency

    task["impact"] = impact

    task["overdue_score"] = overdue_score

    score = (
        0.40 * criticality
        + 0.30 * urgency
        + 0.20 * impact
        + 0.10 * overdue_score
    )

    return round(score, 1)


# ============================================================
# PRIORITY LABEL
# ============================================================

def get_priority_label(score: float) -> str:

    if score >= 85:
        return "Critical"

    if score >= 70:
        return "High"

    if score >= 55:
        return "Medium"

    return "Low"


# ============================================================
# TRAIN GAP DETECTION
# ============================================================

def find_block_gaps(
    section_id: int = 1,
    day: str = "Mon",
    min_gap_minutes: int = 60
):
    """
    Read the train schedule and find available maintenance
    windows between train movements.
    """

    conn = get_conn()

    rows = conn.execute(
        """
        SELECT
            departure_time,
            arrival_time,
            train_no,
            train_name,
            train_type

        FROM train_schedule

        WHERE section_id = ?
        AND day_of_week = ?

        ORDER BY departure_time
        """,
        (
            section_id,
            day,
        ),
    ).fetchall()

    conn.close()

    # --------------------------------------------------------
    # NO TRAINS
    # --------------------------------------------------------

    if not rows:

        return [
            {
                "start": "06:00",
                "end": "18:00",
                "duration_hours": 12.0,
                "suitability": 90,
                "reason": "No trains scheduled",
            }
        ]

    # --------------------------------------------------------
    # CREATE OCCUPIED TRAIN WINDOWS
    # --------------------------------------------------------

    occupied = []

    for row in rows:

        start = time_to_min(
            row["departure_time"]
        )

        end = time_to_min(
            row["arrival_time"]
        )

        if end < start:

            end += 24 * 60

        # Safety buffer around train movement

        occupied.append(
            (
                max(0, start - 10),
                min(24 * 60, end + 10),
            )
        )

    # --------------------------------------------------------
    # MERGE OVERLAPPING TRAIN WINDOWS
    # --------------------------------------------------------

    occupied.sort()

    merged = []

    for start, end in occupied:

        if (
            merged
            and start <= merged[-1][1]
        ):

            merged[-1] = (

                merged[-1][0],

                max(
                    merged[-1][1],
                    end
                ),

            )

        else:

            merged.append(
                [start, end]
            )

    # --------------------------------------------------------
    # FIND AVAILABLE GAPS
    # --------------------------------------------------------

    gaps = []

    cursor = 5 * 60

    day_end = (
        23 * 60 + 30
    )

    for start, end in merged:

        if (
            start - cursor
            >= min_gap_minutes
        ):

            duration_hours = (
                start - cursor
            ) / 60

            midpoint = (
                cursor + start
            ) / 2

            # Prefer mid-day and night windows

            if (
                10 * 60
                <= midpoint
                <= 14 * 60
            ):

                suitability = (
                    85
                    + min(
                        10,
                        duration_hours
                    )
                )

            elif (
                midpoint >= 21 * 60
                or midpoint <= 6 * 60
            ):

                suitability = (
                    80
                    + min(
                        10,
                        duration_hours
                    )
                )

            else:

                suitability = (
                    60
                    + min(
                        15,
                        duration_hours
                    )
                )

            gaps.append({

                "start":

                    min_to_time(
                        cursor
                    ),

                "end":

                    min_to_time(
                        start
                    ),

                "duration_hours":

                    round(
                        duration_hours,
                        1
                    ),

                "suitability":

                    round(
                        suitability,
                        1
                    ),

                "reason":

                    "Free window between trains",

            })

        cursor = max(
            cursor,
            end
        )

    # --------------------------------------------------------
    # FINAL GAP
    # --------------------------------------------------------

    if (
        day_end - cursor
        >= min_gap_minutes
    ):

        duration_hours = (
            day_end - cursor
        ) / 60

        gaps.append({

            "start":

                min_to_time(
                    cursor
                ),

            "end":

                min_to_time(
                    day_end
                ),

            "duration_hours":

                round(
                    duration_hours,
                    1
                ),

            "suitability": 75,

            "reason":

                "Evening free window",

        })

    # Best gaps first

    gaps.sort(

        key=lambda gap:

            -gap["suitability"]

    )

    return gaps


# ============================================================
# DEPARTMENT-SPECIFIC RESOURCE CHECK
# ============================================================

def check_resources(
    day: str,
    tasks: list
) -> dict:
    """
    Check whether the correct resources are available.

    Engineering Tasks
        -> Engineering Workers

    S&T Tasks
        -> Signal Workers

    Traction Tasks
        -> TRD Workers

    Special resources:
        -> Crane
        -> Tower Wagon
        -> Welding Unit
        -> Supervisors
    """

    conn = get_conn()

    # --------------------------------------------------------
    # CALCULATE WORKER REQUIREMENTS BY DEPARTMENT
    # --------------------------------------------------------

    worker_requirements = {

        "Engineering": 0,

        "S&T": 0,

        "Traction": 0,

    }

    for task in tasks:

        department = task.get(
            "department"
        )

        required_workers = task.get(
            "required_workers",
            4
        )

        if (
            department
            in worker_requirements
        ):

            worker_requirements[
                department
            ] += required_workers

    # --------------------------------------------------------
    # GET RESOURCE AVAILABILITY
    # --------------------------------------------------------

    def get_available(resource_id):

        row = conn.execute(
            """
            SELECT available_count

            FROM resource_availability

            WHERE resource_id = ?

            AND day_of_week = ?

            AND shift = 'day'
            """,
            (
                resource_id,
                day,
            ),
        ).fetchone()

        if row:

            return row[
                "available_count"
            ]

        return 0

    # --------------------------------------------------------
    # DEPARTMENT-SPECIFIC WORKERS
    # --------------------------------------------------------

    engineering_workers = (

        get_available(1)

        + get_available(2)

    )

    signal_workers = get_available(3)

    traction_workers = get_available(4)

    # --------------------------------------------------------
    # SPECIAL RESOURCES
    # --------------------------------------------------------

    crane_available = get_available(5)

    tower_wagon_available = get_available(6)

    welding_available = get_available(7)

    supervisors_available = get_available(8)

    conn.close()

    # --------------------------------------------------------
    # RESOURCE CHECK RESULTS
    # --------------------------------------------------------

    details = []

    ok = True

    # ========================================================
    # ENGINEERING WORKERS
    # ========================================================

    engineering_required = (

        worker_requirements[
            "Engineering"
        ]

    )

    if engineering_required > 0:

        status = (

            "Available"

            if (
                engineering_workers
                >= engineering_required
            )

            else "Shortage"

        )

        details.append({

            "item":

                "Engineering Workers",

            "department":

                "Engineering",

            "required":

                engineering_required,

            "available":

                engineering_workers,

            "status":

                status,

        })

        if (

            engineering_workers
            < engineering_required

        ):

            ok = False

    # ========================================================
    # SIGNAL WORKERS
    # ========================================================

    signal_required = (

        worker_requirements[
            "S&T"
        ]

    )

    if signal_required > 0:

        status = (

            "Available"

            if (
                signal_workers
                >= signal_required
            )

            else "Shortage"

        )

        details.append({

            "item":

                "Signal Workers",

            "department":

                "S&T",

            "required":

                signal_required,

            "available":

                signal_workers,

            "status":

                status,

        })

        if (

            signal_workers
            < signal_required

        ):

            ok = False

    # ========================================================
    # TRACTION WORKERS
    # ========================================================

    traction_required = (

        worker_requirements[
            "Traction"
        ]

    )

    if traction_required > 0:

        status = (

            "Available"

            if (
                traction_workers
                >= traction_required
            )

            else "Shortage"

        )

        details.append({

            "item":

                "TRD Workers",

            "department":

                "Traction",

            "required":

                traction_required,

            "available":

                traction_workers,

            "status":

                status,

        })

        if (

            traction_workers
            < traction_required

        ):

            ok = False

    # ========================================================
    # SUPERVISORS
    # ========================================================

    departments_involved = len(

        [

            department

            for department, count

            in worker_requirements.items()

            if count > 0

        ]

    )

    supervisor_required = max(

        1,

        departments_involved,

    )

    supervisor_status = (

        "Available"

        if (
            supervisors_available
            >= supervisor_required
        )

        else "Shortage"

    )

    details.append({

        "item":

            "JE/SSE Supervisors",

        "required":

            supervisor_required,

        "available":

            supervisors_available,

        "status":

            supervisor_status,

    })

    if (

        supervisors_available
        < supervisor_required

    ):

        ok = False

    # ========================================================
    # CRANE
    # ========================================================

    requires_crane = any(

        task.get(
            "requires_crane"
        )

        for task in tasks

    )

    if requires_crane:

        status = (

            "Available"

            if crane_available >= 1

            else "Not available"

        )

        details.append({

            "item":

                "Rail Crane",

            "required": 1,

            "available":

                crane_available,

            "status":

                status,

        })

        if crane_available < 1:

            ok = False

    # ========================================================
    # TOWER WAGON
    # ========================================================

    requires_tower_wagon = any(

        task.get(
            "requires_tower_wagon"
        )

        for task in tasks

    )

    if requires_tower_wagon:

        status = (

            "Available"

            if (
                tower_wagon_available
                >= 1
            )

            else "Not available"

        )

        details.append({

            "item":

                "Tower Wagon",

            "required": 1,

            "available":

                tower_wagon_available,

            "status":

                status,

        })

        if (

            tower_wagon_available
            < 1

        ):

            ok = False

    # ========================================================
    # WELDING UNIT
    # ========================================================

    requires_welding = any(

        task.get(
            "requires_welding"
        )

        for task in tasks

    )

    if requires_welding:

        status = (

            "Available"

            if welding_available >= 1

            else "Shortage"

        )

        details.append({

            "item":

                "Welding Unit",

            "required": 1,

            "available":

                welding_available,

            "status":

                status,

        })

        if welding_available < 1:

            ok = False

    # --------------------------------------------------------
    # GENERATE NOTES
    # --------------------------------------------------------

    notes = []

    for item in details:

        if (

            item["status"]
            != "Available"

        ):

            notes.append(

                f"{item['item']}: "

                f"need {item['required']}, "

                f"have {item['available']}"

            )

    return {

        "ok":

            ok,

        "details":

            details,

        "notes":

            (

                "; ".join(notes)

                if notes

                else "All required resources available"

            ),

        "summary":

            (

                "READY"

                if ok

                else "SHORTAGE"

            ),

    }


# ============================================================
# ROLE ASSIGNMENT
# ============================================================

def assign_roles(
    tasks: list
) -> list:
    """
    Assign required roles based on department
    and task requirements.
    """

    assignments = []

    for task in tasks:

        department = task[
            "department"
        ]

        # ----------------------------------------------------
        # ENGINEERING
        # ----------------------------------------------------

        if department == "Engineering":

            roles = [

                "SSE/JE (P.Way)",

                "P.Way Gang",

            ]

            if task.get(
                "requires_welding"
            ):

                roles.append(
                    "Welder"
                )

            if task.get(
                "requires_crane"
            ):

                roles.append(
                    "Crane Operator"
                )

        # ----------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------

        elif department == "S&T":

            roles = [

                "JE (Signal)",

                "Signal Maintainer",

            ]

        # ----------------------------------------------------
        # TRACTION
        # ----------------------------------------------------

        elif department == "Traction":

            roles = [

                "JE (TRD)",

                "TRD Gang",

            ]

            if task.get(
                "requires_tower_wagon"
            ):

                roles.append(
                    "Tower Wagon Operator"
                )

        # ----------------------------------------------------
        # DEFAULT
        # ----------------------------------------------------

        else:

            roles = [

                "Supervisor"

            ]

        assignments.append({

            "task_code":

                task["task_code"],

            "description":

                task["description"],

            "department":

                department,

            "roles":

                roles,

        })

    return assignments


# ============================================================
# BLOCK PROPOSAL GENERATION
# ============================================================

def generate_block_proposals(
    section_id: int = 1,
    days: list = None
):
    """
    Generate feasible maintenance block proposals.

    Scheduling process:

    1. Load pending tasks.
    2. Calculate priority.
    3. Sort tasks by priority.
    4. Find train-free gaps.
    5. Try tasks one by one.
    6. Check time constraints.
    7. Check department-specific resources.
    8. Add only feasible tasks.
    9. Generate maintenance block.
    """

    # --------------------------------------------------------
    # DEFAULT DAYS
    # --------------------------------------------------------

    if days is None:

        days = [

            "Mon",

            "Tue",

            "Wed",

            "Thu",

            "Fri",

            "Sat",

        ]

    # --------------------------------------------------------
    # LOAD PENDING TASKS
    # --------------------------------------------------------

    conn = get_conn()

    task_rows = conn.execute(
        """
        SELECT *

        FROM tasks

        WHERE section_id = ?

        AND status = 'pending'
        """,
        (
            section_id,
        ),
    ).fetchall()

    conn.close()

    tasks = [

        dict(row)

        for row in task_rows

    ]

    # --------------------------------------------------------
    # CALCULATE PRIORITY
    # --------------------------------------------------------

    for task in tasks:

        task["ai_score"] = (

            compute_priority(
                task
            )

        )

        task["priority"] = (

            get_priority_label(
                task["ai_score"]
            )

        )

    # Highest priority first

    tasks.sort(

        key=lambda task:

            -task["ai_score"]

    )

    # --------------------------------------------------------
    # INITIALIZE
    # --------------------------------------------------------

    proposals = []

    used_task_ids = set()

    block_num = 1

    # --------------------------------------------------------
    # PROCESS EACH DAY
    # --------------------------------------------------------

    for day in days:

        gaps = find_block_gaps(

            section_id,

            day,

            min_gap_minutes=60,

        )

        if not gaps:

            continue

        # ----------------------------------------------------
        # PROCESS BEST GAPS
        # ----------------------------------------------------

        for gap in gaps[:4]:

            # Remaining tasks only

            remaining_tasks = [

                task

                for task in tasks

                if task["id"]
                not in used_task_ids

            ]

            if not remaining_tasks:

                break

            selected = []

            hours_left = gap[
                "duration_hours"
            ]

            # ------------------------------------------------
            # TRY TASKS ONE BY ONE
            # ------------------------------------------------

            for task in remaining_tasks:

                # --------------------------------------------
                # CHECK TIME CONSTRAINT
                # --------------------------------------------

                if (

                    task["est_hours"]

                    > hours_left + 0.5

                ):

                    continue

                # --------------------------------------------
                # TEMPORARILY ADD TASK
                # --------------------------------------------

                test_selection = (

                    selected

                    + [task]

                )

                # --------------------------------------------
                # CHECK RESOURCES
                # --------------------------------------------

                resource_check = (

                    check_resources(

                        day,

                        test_selection,

                    )

                )

                # --------------------------------------------
                # ACCEPT TASK ONLY IF FEASIBLE
                # --------------------------------------------

                if resource_check["ok"]:

                    selected.append(
                        task
                    )

                    hours_left -= (

                        task[
                            "est_hours"
                        ]

                    )

                # Otherwise:
                # Skip task and continue checking
                # lower-priority tasks.

            # ------------------------------------------------
            # NO FEASIBLE TASKS
            # ------------------------------------------------

            if not selected:

                continue

            # ------------------------------------------------
            # FINAL RESOURCE CHECK
            # ------------------------------------------------

            resource_check = (

                check_resources(

                    day,

                    selected,

                )

            )

            if not resource_check["ok"]:

                continue

            # ------------------------------------------------
            # ASSIGN ROLES
            # ------------------------------------------------

            role_assignments = (

                assign_roles(
                    selected
                )

            )

            # ------------------------------------------------
            # CALCULATE BLOCK PRIORITY
            # ------------------------------------------------

            avg_score = (

                sum(

                    task["ai_score"]

                    for task in selected

                )

                / len(selected)

            )

            # ------------------------------------------------
            # CREATE PROPOSAL
            # ------------------------------------------------

            proposals.append({

                "block_code":

                    f"BLK-DG-{block_num:03d}",

                "section":

                    "Delhi–Ghaziabad",

                "day":

                    day,

                "start_time":

                    gap["start"],

                "end_time":

                    gap["end"],

                "duration_hours":

                    gap[
                        "duration_hours"
                    ],

                "gap_reason":

                    gap[
                        "reason"
                    ],

                "suitability":

                    gap[
                        "suitability"
                    ],

                "ai_score":

                    round(
                        avg_score,
                        1
                    ),

                "tasks":

                    selected,

                "resource_check":

                    resource_check,

                "role_assignments":

                    role_assignments,

                "status":

                    "proposed",

            })

            # ------------------------------------------------
            # MARK TASKS AS USED
            # ------------------------------------------------

            for task in selected:

                used_task_ids.add(

                    task["id"]

                )

            block_num += 1

    return proposals


# ============================================================
# SAVE PROPOSALS TO DATABASE
# ============================================================

def save_proposals(
    proposals: list
):
    """
    Save generated block proposals
    for officer approval.
    """

    conn = get_conn()

    cursor = conn.cursor()

    # Remove previous generated proposals

    cursor.execute(
        "DELETE FROM block_assignments"
    )

    cursor.execute(
        "DELETE FROM approvals"
    )

    cursor.execute(
        "DELETE FROM proposed_blocks"
    )

    # --------------------------------------------------------
    # SAVE EACH BLOCK
    # --------------------------------------------------------

    for proposal in proposals:

        cursor.execute(
            """
            INSERT INTO proposed_blocks
            (
                block_code,
                section_id,
                day_of_week,
                start_time,
                end_time,
                duration_hours,
                status,
                ai_score,
                resource_status,
                resource_notes
            )

            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (

                proposal[
                    "block_code"
                ],

                1,

                proposal[
                    "day"
                ],

                proposal[
                    "start_time"
                ],

                proposal[
                    "end_time"
                ],

                proposal[
                    "duration_hours"
                ],

                "proposed",

                proposal[
                    "ai_score"
                ],

                proposal[
                    "resource_check"
                ][
                    "summary"
                ],

                proposal[
                    "resource_check"
                ][
                    "notes"
                ],

            ),
        )

        block_id = cursor.lastrowid

        # ----------------------------------------------------
        # SAVE TASK ASSIGNMENTS
        # ----------------------------------------------------

        for task in proposal["tasks"]:

            cursor.execute(
                """
                INSERT INTO block_assignments
                (
                    block_id,
                    task_id,
                    assigned_role
                )

                VALUES (?,?,?)
                """,
                (

                    block_id,

                    task["id"],

                    task[
                        "department"
                    ],

                ),
            )

    conn.commit()

    conn.close()


# ============================================================
# WHAT-IF: DELAY SIMULATION
# ============================================================

def whatif_delay(
    block_code: str,
    delay_hours: float
) -> dict:
    """
    Simulate the effect of delaying a block.

    Note:
    This is currently a prototype simulation
    using configurable assumptions.
    """

    conn = get_conn()

    block = conn.execute(
        """
        SELECT *

        FROM proposed_blocks

        WHERE block_code = ?
        """,
        (
            block_code,
        ),
    ).fetchone()

    conn.close()

    if not block:

        return {

            "error":

                "Block not found"

        }

    # Prototype assumptions

    base_availability = 94.2

    impact = (

        delay_hours * 0.35

    )

    if (

        block["ai_score"]

        and block["ai_score"] >= 85

    ):

        impact += 1.0

    new_availability = round(

        base_availability - impact,

        1,

    )

    return {

        "scenario":

            "delay",

        "block_code":

            block_code,

        "delay_hours":

            delay_hours,

        "original_window":

            (
                f"{block['day_of_week']} "

                f"{block['start_time']}"

                f"–{block['end_time']}"
            ),

        "projected_availability":

            new_availability,

        "availability_drop":

            round(
                impact,
                1
            ),

        "effects":

            [

                f"Asset availability drops by "

                f"~{impact:.1f}%",

                "Downstream blocks may shift",

                "Risk of train punctuality impact",

                (

                    "Critical defects remain open longer"

                    if (
                        block["ai_score"]
                        or 0
                    ) >= 85

                    else

                    "Medium priority work deferred"

                ),

            ],

        "ai_suggestion":

            (

                "Prefer re-slotting within "

                "the next 24–48 hours using "

                "the next feasible train gap."

            ),

    }


# ============================================================
# WHAT-IF: WEATHER SIMULATION
# ============================================================

def whatif_weather(
    block_code: str,
    weather: str
) -> dict:
    """
    Prototype weather impact simulation.

    This is currently rule-based,
    not machine-learning weather prediction.
    """

    weather = weather.lower()

    outdoor_risk = {

        "rain":

            (
                "High",

                "Track and OHE outdoor work "
                "requires additional safety review.",
            ),

        "heavy_rain":

            (
                "Critical",

                "Outdoor maintenance should "
                "generally be postponed.",
            ),

        "fog":

            (
                "Medium",

                "Visibility restrictions may "
                "affect signalling operations.",
            ),

        "heat":

            (
                "Medium",

                "Limit continuous outdoor work.",
            ),

        "storm":

            (
                "Critical",

                "Cancel unsafe work and secure "
                "the maintenance site.",
            ),

    }

    level, message = outdoor_risk.get(

        weather,

        (
            "Low",

            "No major restriction",
        ),

    )

    return {

        "scenario":

            "weather",

        "block_code":

            block_code,

        "weather":

            weather,

        "risk_level":

            level,

        "message":

            message,

        "ai_actions":

            [

                "Re-evaluate outdoor Engineering tasks",

                "Re-evaluate Traction work",

                "Keep safe indoor S&T work where possible",

                "Move crane-dependent work if required",

                "Notify officer for approval",

            ],

        "recommended":

            (

                "Postpone"

                if level in (

                    "High",

                    "Critical",

                )

                else

                "Proceed with caution"

            ),

    }


# ============================================================
# LIST TASKS WITH PRIORITY
# ============================================================

def list_tasks_with_priority():
    """
    Return all tasks with calculated priority
    and score explanations.
    """

    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *

        FROM tasks

        WHERE section_id = 1
        """
    ).fetchall()

    conn.close()

    output = []

    for row in rows:

        task = dict(row)

        task["ai_score"] = (

            compute_priority(
                task
            )

        )

        task["priority"] = (

            get_priority_label(
                task["ai_score"]
            )

        )

        output.append(
            task
        )

    # Highest priority first

    output.sort(

        key=lambda task:

            -task["ai_score"]

    )

    return output
```
