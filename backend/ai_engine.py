"""
RailBlock AI - AI / Optimization Engine

This module handles:

1. Task priority calculation
2. Train-free maintenance gap detection
3. Resource availability checking
4. Role assignment
5. Multi-criteria block scheduling
6. Block proposal generation
7. Saving proposals
8. What-if delay analysis
9. What-if weather analysis

IMPORTANT:

This is NOT Machine Learning.

The system uses a:

Multi-Criteria + Constraint-Based Heuristic Optimization Algorithm

The system combines:

- Task Criticality
- Task Urgency
- Operational Impact
- Overdue Days
- Train-free Gap Suitability
- Time Utilization
- Resource Availability

to generate maintenance block proposals.
"""

from datetime import datetime, timedelta
from typing import Dict, List

from database import get_conn


# ============================================================
# CONFIGURATION
# ============================================================

# Priority weights
#
# These values determine how much each factor contributes
# to the final task priority.

WEIGHT_CRITICALITY = 0.35
WEIGHT_URGENCY = 0.30
WEIGHT_IMPACT = 0.25
WEIGHT_OVERDUE = 0.10


# Scheduling score weights

WEIGHT_TASK_PRIORITY = 0.70
WEIGHT_GAP_SUITABILITY = 0.20
WEIGHT_TIME_FIT = 0.10


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    """
    Restrict a value between minimum and maximum.
    """

    return max(minimum, min(value, maximum))


def time_to_minutes(time_string: str) -> int:
    """
    Convert HH:MM into total minutes.

    Example:

    "10:30"

    becomes:

    630 minutes
    """

    hours, minutes = map(int, time_string.split(":"))

    return hours * 60 + minutes


def minutes_to_time(total_minutes: int) -> str:
    """
    Convert total minutes into HH:MM format.
    """

    total_minutes = total_minutes % (24 * 60)

    hours = total_minutes // 60
    minutes = total_minutes % 60

    return f"{hours:02d}:{minutes:02d}"


def get_priority_label(score: float) -> str:
    """
    Convert numerical priority score into a readable label.
    """

    if score >= 85:
        return "CRITICAL"

    if score >= 70:
        return "HIGH"

    if score >= 50:
        return "MEDIUM"

    return "LOW"


# ============================================================
# PRIORITY CALCULATION
# ============================================================

def calculate_overdue_score(overdue_days: int) -> float:
    """
    Convert overdue days into a score between 0 and 100.

    Logic:

    0 overdue days   -> 0 score
    10 overdue days  -> 50 score
    20+ overdue days -> 100 score

    The score is capped at 100.
    """

    overdue_days = max(0, overdue_days)

    overdue_score = overdue_days * 5

    return clamp(overdue_score)


def compute_priority(task: Dict) -> float:
    """
    Calculate the final priority score of a maintenance task.

    Formula:

    Priority Score =

        Criticality × 35%
        +
        Urgency × 30%
        +
        Impact × 25%
        +
        Overdue Score × 10%

    All input values are expected to be between 0 and 100.

    This is a weighted multi-criteria decision algorithm.
    """

    criticality = float(task.get("criticality", 0))
    urgency = float(task.get("urgency", 0))
    impact = float(task.get("impact", 0))

    overdue_days = int(task.get("overdue_days", 0))

    overdue_score = calculate_overdue_score(
        overdue_days
    )

    priority_score = (

        criticality * WEIGHT_CRITICALITY

        +

        urgency * WEIGHT_URGENCY

        +

        impact * WEIGHT_IMPACT

        +

        overdue_score * WEIGHT_OVERDUE

    )

    return round(
        clamp(priority_score),
        1
    )


def get_priority_explanation(task: Dict) -> Dict:
    """
    Return a detailed explanation of how the priority score
    was calculated.

    Useful for:

    - SIH demonstration
    - Explainable AI concept
    - Debugging
    - Judge questions
    """

    criticality = float(
        task.get("criticality", 0)
    )

    urgency = float(
        task.get("urgency", 0)
    )

    impact = float(
        task.get("impact", 0)
    )

    overdue_days = int(
        task.get("overdue_days", 0)
    )

    overdue_score = calculate_overdue_score(
        overdue_days
    )

    criticality_contribution = round(
        criticality * WEIGHT_CRITICALITY,
        2
    )

    urgency_contribution = round(
        urgency * WEIGHT_URGENCY,
        2
    )

    impact_contribution = round(
        impact * WEIGHT_IMPACT,
        2
    )

    overdue_contribution = round(
        overdue_score * WEIGHT_OVERDUE,
        2
    )

    final_score = round(

        criticality_contribution

        +

        urgency_contribution

        +

        impact_contribution

        +

        overdue_contribution,

        1

    )

    return {

        "criticality": criticality,

        "urgency": urgency,

        "impact": impact,

        "overdue_days": overdue_days,

        "overdue_score": overdue_score,

        "criticality_contribution":
            criticality_contribution,

        "urgency_contribution":
            urgency_contribution,

        "impact_contribution":
            impact_contribution,

        "overdue_contribution":
            overdue_contribution,

        "final_score": final_score,

        "priority":
            get_priority_label(final_score),

    }


# ============================================================
# LIST TASKS WITH PRIORITY
# ============================================================

def list_tasks_with_priority() -> List[Dict]:
    """
    Load all tasks from the database.

    Calculate priority for every task.

    Return tasks sorted from highest priority
    to lowest priority.
    """

    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM tasks
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    tasks = []

    for row in rows:

        task = dict(row)

        ai_score = compute_priority(
            task
        )

        task["ai_score"] = ai_score

        task["priority"] = (
            get_priority_label(ai_score)
        )

        task["priority_explanation"] = (
            get_priority_explanation(task)
        )

        tasks.append(task)

    # Highest priority first

    tasks.sort(

        key=lambda task:
            task["ai_score"],

        reverse=True

    )

    return tasks


# ============================================================
# GAP SUITABILITY
# ============================================================

def calculate_gap_suitability(
    duration_hours: float,
    start_time: str,
    end_time: str
) -> float:
    """
    Calculate how suitable a train-free gap is
    for maintenance work.

    Factors considered:

    1. Gap duration
    2. Time of day

    Longer gaps are generally more useful.

    Night and off-peak periods can receive
    additional suitability.
    """

    score = 0

    # --------------------------------------------------------
    # DURATION SCORE
    # --------------------------------------------------------

    if duration_hours >= 6:

        score += 70

    elif duration_hours >= 4:

        score += 60

    elif duration_hours >= 3:

        score += 50

    elif duration_hours >= 2:

        score += 40

    elif duration_hours >= 1:

        score += 25

    else:

        score += 10

    # --------------------------------------------------------
    # TIME OF DAY SCORE
    # --------------------------------------------------------

    start_hour = int(
        start_time.split(":")[0]
    )

    # Night / early morning

    if start_hour >= 22 or start_hour < 6:

        score += 25

    # Midday

    elif 10 <= start_hour < 16:

        score += 15

    # Other periods

    else:

        score += 5

    return round(
        clamp(score),
        1
    )


# ============================================================
# FIND TRAIN-FREE BLOCK GAPS
# ============================================================

def find_block_gaps(
    section_id: int,
    day: str,
    min_gap_minutes: int = 60
) -> List[Dict]:
    """
    Find train-free maintenance windows.

    Process:

    1. Load train schedule for selected day.
    2. Sort trains by departure time.
    3. Find time between one train and the next.
    4. Keep gaps larger than minimum duration.
    5. Calculate suitability score.

    IMPORTANT:

    This prototype uses the train schedule stored
    in the database.

    In a real railway deployment, this would require:

    - Live train movement data
    - Traffic control integration
    - Signalling constraints
    - Safety margins
    """

    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM train_schedule

        WHERE section_id = ?
        AND day_of_week = ?

        ORDER BY departure_time
        """,
        (
            section_id,
            day
        ),
    ).fetchall()

    conn.close()

    trains = [

        dict(row)

        for row in rows

    ]

    gaps = []

    # --------------------------------------------------------
    # NO TRAINS
    # --------------------------------------------------------

    if not trains:

        return gaps

    # --------------------------------------------------------
    # START OF DAY
    # --------------------------------------------------------

    day_start = 0

    first_train_start = time_to_minutes(
        trains[0]["departure_time"]
    )

    initial_gap = (

        first_train_start
        -
        day_start

    )

    if initial_gap >= min_gap_minutes:

        start_time = "00:00"

        end_time = trains[0][
            "departure_time"
        ]

        duration_hours = round(
            initial_gap / 60,
            2
        )

        suitability = (
            calculate_gap_suitability(
                duration_hours,
                start_time,
                end_time
            )
        )

        gaps.append({

            "start":
                start_time,

            "end":
                end_time,

            "duration_minutes":
                initial_gap,

            "duration_hours":
                duration_hours,

            "suitability":
                suitability,

            "reason":
                "Before first scheduled train",

        })

    # --------------------------------------------------------
    # GAPS BETWEEN TRAINS
    # --------------------------------------------------------

    for index in range(
        len(trains) - 1
    ):

        current_train = trains[index]

        next_train = trains[
            index + 1
        ]

        # Current train clears section

        current_end = time_to_minutes(

            current_train[
                "arrival_time"
            ]

        )

        # Next train enters section

        next_start = time_to_minutes(

            next_train[
                "departure_time"
            ]

        )

        gap_minutes = (

            next_start
            -
            current_end

        )

        if gap_minutes >= min_gap_minutes:

            start_time = (
                current_train[
                    "arrival_time"
                ]
            )

            end_time = (
                next_train[
                    "departure_time"
                ]
            )

            duration_hours = round(

                gap_minutes / 60,

                2

            )

            suitability = (

                calculate_gap_suitability(

                    duration_hours,

                    start_time,

                    end_time

                )

            )

            gaps.append({

                "start":
                    start_time,

                "end":
                    end_time,

                "duration_minutes":
                    gap_minutes,

                "duration_hours":
                    duration_hours,

                "suitability":
                    suitability,

                "reason":
                    (
                        "Gap between "
                        f"{current_train['train_no']} "
                        "and "
                        f"{next_train['train_no']}"
                    ),

            })

    # --------------------------------------------------------
    # END OF DAY
    # --------------------------------------------------------

    last_train = trains[-1]

    last_train_end = time_to_minutes(

        last_train[
            "arrival_time"
        ]

    )

    day_end = 24 * 60

    final_gap = (

        day_end
        -
        last_train_end

    )

    if final_gap >= min_gap_minutes:

        start_time = (

            last_train[
                "arrival_time"
            ]

        )

        end_time = "24:00"

        duration_hours = round(

            final_gap / 60,

            2

        )

        suitability = (

            calculate_gap_suitability(

                duration_hours,

                start_time,

                end_time

            )

        )

        gaps.append({

            "start":
                start_time,

            "end":
                end_time,

            "duration_minutes":
                final_gap,

            "duration_hours":
                duration_hours,

            "suitability":
                suitability,

            "reason":
                "After last scheduled train",

        })

    # --------------------------------------------------------
    # SORT GAPS
    # --------------------------------------------------------

    gaps.sort(

        key=lambda gap:

            gap["suitability"],

        reverse=True

    )

    return gaps


# ============================================================
# RESOURCE CHECKING
# ============================================================

def check_resources(
    day: str,
    tasks: List[Dict]
) -> Dict:
    """
    Check whether all required resources
    are available.

    Resources checked:

    - Workers
    - Crane
    - Tower Wagon
    - Welding Unit

    Returns:

    {
        "ok": True / False,
        "notes": [...],
        "requirements": {...}
    }
    """

    conn = get_conn()

    notes = []

    requirements = {

        "workers_by_department": {},

        "crane_required": False,

        "tower_wagon_required": False,

        "welding_required": False,

    }

    # --------------------------------------------------------
    # CALCULATE REQUIREMENTS
    # --------------------------------------------------------

    for task in tasks:

        department = task.get(

            "department",

            "Unknown"

        )

        required_workers = int(

            task.get(

                "required_workers",

                0

            )

        )

        requirements[
            "workers_by_department"
        ][department] = (

            requirements[
                "workers_by_department"
            ].get(

                department,

                0

            )

            +

            required_workers

        )

        if int(
            task.get(
                "requires_crane",
                0
            )
        ):

            requirements[
                "crane_required"
            ] = True

        if int(
            task.get(
                "requires_tower_wagon",
                0
            )
        ):

            requirements[
                "tower_wagon_required"
            ] = True

        if int(
            task.get(
                "requires_welding",
                0
            )
        ):

            requirements[
                "welding_required"
            ] = True

    # --------------------------------------------------------
    # CHECK WORKERS BY DEPARTMENT
    # --------------------------------------------------------

    for department, required in (

        requirements[
            "workers_by_department"
        ].items()

    ):

        row = conn.execute(

            """
            SELECT
                COALESCE(
                    SUM(ra.available_count),
                    0
                ) AS available

            FROM resources r

            JOIN resource_availability ra

                ON ra.resource_id = r.id

            WHERE
                r.resource_type = 'workers'

            AND
                r.department = ?

            AND
                ra.day_of_week = ?
            """,

            (
                department,
                day
            ),

        ).fetchone()

        available = (

            row["available"]

            if row

            else 0

        )

        if available < required:

            notes.append(

                f"Insufficient workers for "
                f"{department}: "

                f"Required {required}, "

                f"Available {available}"

            )

        else:

            notes.append(

                f"{department} workers available: "

                f"{available} available, "

                f"{required} required"

            )

    # --------------------------------------------------------
    # CHECK CRANE
    # --------------------------------------------------------

    if requirements["crane_required"]:

        row = conn.execute(

            """
            SELECT
                COALESCE(
                    SUM(ra.available_count),
                    0
                ) AS available

            FROM resources r

            JOIN resource_availability ra

                ON ra.resource_id = r.id

            WHERE
                r.resource_type = 'crane'

            AND
                ra.day_of_week = ?
            """,

            (day,),

        ).fetchone()

        available = (

            row["available"]

            if row

            else 0

        )

        if available < 1:

            notes.append(

                "Crane required but unavailable"

            )

        else:

            notes.append(

                "Crane available"

            )

    # --------------------------------------------------------
    # CHECK TOWER WAGON
    # --------------------------------------------------------

    if requirements[
        "tower_wagon_required"
    ]:

        row = conn.execute(

            """
            SELECT
                COALESCE(
                    SUM(ra.available_count),
                    0
                ) AS available

            FROM resources r

            JOIN resource_availability ra

                ON ra.resource_id = r.id

            WHERE
                r.resource_type = 'tower_wagon'

            AND
                ra.day_of_week = ?
            """,

            (day,),

        ).fetchone()

        available = (

            row["available"]

            if row

            else 0

        )

        if available < 1:

            notes.append(

                "Tower Wagon required but unavailable"

            )

        else:

            notes.append(

                "Tower Wagon available"

            )

    # --------------------------------------------------------
    # CHECK WELDING UNIT
    # --------------------------------------------------------

    if requirements[
        "welding_required"
    ]:

        row = conn.execute(

            """
            SELECT
                COALESCE(
                    SUM(ra.available_count),
                    0
                ) AS available

            FROM resources r

            JOIN resource_availability ra

                ON ra.resource_id = r.id

            WHERE
                r.resource_type = 'welding'

            AND
                ra.day_of_week = ?
            """,

            (day,),

        ).fetchone()

        available = (

            row["available"]

            if row

            else 0

        )

        if available < 1:

            notes.append(

                "Welding Unit required but unavailable"

            )

        else:

            notes.append(

                "Welding Unit available"

            )

    conn.close()

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    failed = any(

        "Insufficient" in note

        or

        "unavailable" in note

        for note in notes

    )

    return {

        "ok":

            not failed,

        "notes":

            notes,

        "requirements":

            requirements,

    }


# ============================================================
# ROLE ASSIGNMENT
# ============================================================

def assign_roles(
    tasks: List[Dict]
) -> List[Dict]:
    """
    Generate suggested role assignments.

    This does NOT assign actual people.

    It assigns required railway roles based
    on the departments involved.
    """

    departments = set(

        task.get(
            "department"
        )

        for task in tasks

    )

    assignments = []

    # --------------------------------------------------------
    # SECTION CONTROLLER
    # --------------------------------------------------------

    assignments.append({

        "role":

            "Section Controller",

        "responsibility":

            (
                "Coordinate block approval "
                "and traffic management"
            ),

    })

    # --------------------------------------------------------
    # ENGINEERING
    # --------------------------------------------------------

    if "Engineering" in departments:

        assignments.append({

            "role":

                "SSE (P.Way)",

            "responsibility":

                (
                    "Supervise track maintenance work"
                ),

        })

    # --------------------------------------------------------
    # SIGNAL & TELECOM
    # --------------------------------------------------------

    if "S&T" in departments:

        assignments.append({

            "role":

                "SSE (Signal)",

            "responsibility":

                (
                    "Supervise signalling work"
                ),

        })

    # --------------------------------------------------------
    # TRACTION
    # --------------------------------------------------------

    if "Traction" in departments:

        assignments.append({

            "role":

                "SSE (TRD)",

            "responsibility":

                (
                    "Supervise OHE and traction work"
                ),

        })

    # --------------------------------------------------------
    # SAFETY SUPERVISION
    # --------------------------------------------------------

    assignments.append({

        "role":

            "Safety Supervisor",

        "responsibility":

            (
                "Verify safety procedures "
                "before and during block"
            ),

    })

    return assignments


# ============================================================
# TIME FIT SCORE
# ============================================================

def calculate_time_fit_score(
    task_hours: float,
    gap_hours: float
) -> float:
    """
    Calculate how efficiently a task fits
    inside an available maintenance gap.

    Formula:

        Task Duration
        -------------
        Gap Duration

        × 100

    Example:

        Task = 2 hours
        Gap = 2.5 hours

        Score = 80

    A task must fit completely inside the gap.
    """

    if gap_hours <= 0:

        return 0

    # Task cannot fit

    if task_hours > gap_hours:

        return 0

    fit_score = (

        task_hours
        /
        gap_hours

    ) * 100

    return round(

        clamp(fit_score),

        1

    )


# ============================================================
# SCHEDULING SCORE
# ============================================================

def calculate_scheduling_score(
    task: Dict,
    gap: Dict
) -> float:
    """
    Calculate how suitable a task is
    for a specific train-free maintenance gap.

    Formula:

        Task Priority     × 70%

        +

        Gap Suitability   × 20%

        +

        Time Fit          × 10%

    Important:

    A task can have different scheduling scores
    for different gaps.
    """

    task_priority = float(

        task.get(

            "ai_score",

            0

        )

    )

    gap_suitability = float(

        gap.get(

            "suitability",

            0

        )

    )

    time_fit = (

        calculate_time_fit_score(

            float(
                task.get(
                    "est_hours",
                    0
                )
            ),

            float(
                gap.get(
                    "duration_hours",
                    0
                )
            ),

        )

    )

    scheduling_score = (

        task_priority
        *
        WEIGHT_TASK_PRIORITY

        +

        gap_suitability
        *
        WEIGHT_GAP_SUITABILITY

        +

        time_fit
        *
        WEIGHT_TIME_FIT

    )

    return round(

        clamp(scheduling_score),

        1

    )


# ============================================================
# GENERATE BLOCK PROPOSALS
# ============================================================

def generate_block_proposals(
    section_id: int = 1,
    days: List[str] = None
) -> List[Dict]:
    """
    Generate optimized maintenance block proposals.

    COMPLETE PROCESS:

    STEP 1:
        Load pending tasks.

    STEP 2:
        Calculate priority score.

    STEP 3:
        Find train-free gaps.

    STEP 4:
        Check whether tasks fit inside each gap.

    STEP 5:
        Calculate scheduling score.

    STEP 6:
        Rank tasks for the specific gap.

    STEP 7:
        Check resource constraints.

    STEP 8:
        Select feasible tasks.

    STEP 9:
        Generate maintenance block proposal.

    This is a constraint-based heuristic
    optimization approach.
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

        (section_id,),

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

            compute_priority(task)

        )

        task["priority"] = (

            get_priority_label(

                task["ai_score"]

            )

        )

    # --------------------------------------------------------
    # SORT BY BASE PRIORITY
    # --------------------------------------------------------

    tasks.sort(

        key=lambda task:

            task["ai_score"],

        reverse=True

    )

    proposals = []

    # Prevent same task from being assigned twice

    used_task_ids = set()

    block_number = 1

    # ========================================================
    # PROCESS EACH DAY
    # ========================================================

    for day in days:

        # ----------------------------------------------------
        # FIND TRAIN-FREE GAPS
        # ----------------------------------------------------

        gaps = find_block_gaps(

            section_id,

            day,

            min_gap_minutes=60,

        )

        if not gaps:

            continue

        # ----------------------------------------------------
        # PROCESS EACH GAP
        # ----------------------------------------------------

        for gap in gaps:

            # ------------------------------------------------
            # REMAINING TASKS
            # ------------------------------------------------

            remaining_tasks = [

                task

                for task in tasks

                if task["id"]

                not in used_task_ids

            ]

            if not remaining_tasks:

                break

            # ------------------------------------------------
            # CALCULATE SCHEDULING SCORE
            # ------------------------------------------------

            scored_tasks = []

            for task in remaining_tasks:

                task_hours = float(

                    task.get(

                        "est_hours",

                        0

                    )

                )

                gap_hours = float(

                    gap.get(

                        "duration_hours",

                        0

                    )

                )

                # --------------------------------------------
                # TASK MUST FIT
                # --------------------------------------------

                if task_hours > gap_hours:

                    continue

                # --------------------------------------------
                # CALCULATE SCHEDULING SCORE
                # --------------------------------------------

                scheduling_score = (

                    calculate_scheduling_score(

                        task,

                        gap

                    )

                )

                time_fit_score = (

                    calculate_time_fit_score(

                        task_hours,

                        gap_hours

                    )

                )

                task_copy = task.copy()

                task_copy[
                    "scheduling_score"
                ] = scheduling_score

                task_copy[
                    "time_fit_score"
                ] = time_fit_score

                scored_tasks.append(

                    task_copy

                )

            # ------------------------------------------------
            # SORT TASKS FOR THIS GAP
            # ------------------------------------------------

            scored_tasks.sort(

                key=lambda task:

                    task[
                        "scheduling_score"
                    ],

                reverse=True

            )

            if not scored_tasks:

                continue

            # ------------------------------------------------
            # SELECT TASKS
            # ------------------------------------------------

            selected = []

            hours_left = float(

                gap[
                    "duration_hours"
                ]

            )

            # ------------------------------------------------
            # TRY TASKS IN ORDER
            # ------------------------------------------------

            for task in scored_tasks:

                task_hours = float(

                    task.get(

                        "est_hours",

                        0

                    )

                )

                # --------------------------------------------
                # CHECK AVAILABLE TIME
                # --------------------------------------------

                if task_hours > hours_left:

                    continue

                # --------------------------------------------
                # TEST RESOURCE AVAILABILITY
                # --------------------------------------------

                test_selection = (

                    selected

                    +

                    [task]

                )

                resource_check = (

                    check_resources(

                        day,

                        test_selection

                    )

                )

                # --------------------------------------------
                # ACCEPT TASK
                # --------------------------------------------

                if resource_check["ok"]:

                    selected.append(

                        task

                    )

                    hours_left -= (

                        task_hours

                    )

            # ------------------------------------------------
            # NO TASK SELECTED
            # ------------------------------------------------

            if not selected:

                continue

            # ------------------------------------------------
            # FINAL RESOURCE CHECK
            # ------------------------------------------------

            resource_check = (

                check_resources(

                    day,

                    selected

                )

            )

            if not resource_check["ok"]:

                continue

            # ------------------------------------------------
            # ROLE ASSIGNMENTS
            # ------------------------------------------------

            role_assignments = (

                assign_roles(

                    selected

                )

            )

            # ------------------------------------------------
            # CALCULATE AVERAGE TASK PRIORITY
            # ------------------------------------------------

            average_ai_score = (

                sum(

                    task["ai_score"]

                    for task in selected

                )

                /

                len(selected)

            )

            # ------------------------------------------------
            # CALCULATE AVERAGE SCHEDULING SCORE
            # ------------------------------------------------

            average_scheduling_score = (

                sum(

                    task[
                        "scheduling_score"
                    ]

                    for task in selected

                )

                /

                len(selected)

            )

            # ------------------------------------------------
            # CALCULATE USED HOURS
            # ------------------------------------------------

            used_hours = (

                sum(

                    float(

                        task.get(

                            "est_hours",

                            0

                        )

                    )

                    for task in selected

                )

            )

            # ------------------------------------------------
            # GAP UTILIZATION
            # ------------------------------------------------

            gap_duration = float(

                gap[
                    "duration_hours"
                ]

            )

            utilization_percent = (

                used_hours

                /

                gap_duration

                *

                100

            )

            utilization_percent = (

                clamp(

                    utilization_percent

                )

            )

            # ------------------------------------------------
            # CREATE BLOCK PROPOSAL
            # ------------------------------------------------

            proposal = {

                "block_code":

                    (
                        f"BLK-DG-"
                        f"{block_number:03d}"
                    ),

                "section":

                    "Delhi–Ghaziabad",

                "day":

                    day,

                "start_time":

                    gap["start"],

                "end_time":

                    gap["end"],

                "duration_hours":

                    round(

                        gap_duration,

                        2

                    ),

                "used_hours":

                    round(

                        used_hours,

                        2

                    ),

                "unused_hours":

                    round(

                        hours_left,

                        2

                    ),

                "utilization_percent":

                    round(

                        utilization_percent,

                        1

                    ),

                "gap_reason":

                    gap["reason"],

                "suitability":

                    gap["suitability"],

                "ai_score":

                    round(

                        average_ai_score,

                        1

                    ),

                "scheduling_score":

                    round(

                        average_scheduling_score,

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

            }

            proposals.append(

                proposal

            )

            # ------------------------------------------------
            # MARK TASKS AS USED
            # ------------------------------------------------

            for task in selected:

                used_task_ids.add(

                    task["id"]

                )

            block_number += 1

    return proposals


# ============================================================
# SAVE PROPOSALS
# ============================================================

def save_proposals(
    proposals: List[Dict]
):
    """
    Save generated block proposals
    into the database.

    Existing proposals are deleted before
    saving new optimization results.
    """

    conn = get_conn()

    cursor = conn.cursor()

    # --------------------------------------------------------
    # REMOVE OLD PROPOSALS
    # --------------------------------------------------------

    cursor.execute(

        "DELETE FROM block_assignments"

    )

    cursor.execute(

        "DELETE FROM proposed_blocks"

    )

    # --------------------------------------------------------
    # SAVE NEW PROPOSALS
    # --------------------------------------------------------

    for proposal in proposals:

        resource_status = (

            "available"

            if proposal[
                "resource_check"
            ]["ok"]

            else

            "unavailable"

        )

        resource_notes = " | ".join(

            proposal[
                "resource_check"
            ]["notes"]

        )

        cursor.execute(

            """
            INSERT INTO proposed_blocks (

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

            VALUES (

                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?

            )
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

                proposal[
                    "status"
                ],

                proposal[
                    "ai_score"
                ],

                resource_status,

                resource_notes,

            ),

        )

        block_id = cursor.lastrowid

        # ----------------------------------------------------
        # SAVE TASK ASSIGNMENTS
        # ----------------------------------------------------

        for task in proposal["tasks"]:

            assigned_role = (

                "Maintenance Team"

            )

            cursor.execute(

                """
                INSERT INTO block_assignments (

                    block_id,

                    task_id,

                    assigned_role,

                    resource_id

                )

                VALUES (

                    ?, ?, ?, ?

                )
                """,

                (

                    block_id,

                    task["id"],

                    assigned_role,

                    None,

                ),

            )

    conn.commit()

    conn.close()


# ============================================================
# WHAT-IF DELAY ANALYSIS
# ============================================================

def whatif_delay(
    block_code: str,
    delay_hours: float = 2.0
) -> Dict:
    """
    Simulate what happens if a maintenance block
    is delayed.

    This does not modify the actual database.
    """

    conn = get_conn()

    block = conn.execute(

        """
        SELECT *

        FROM proposed_blocks

        WHERE block_code = ?
        """,

        (block_code,),

    ).fetchone()

    if not block:

        conn.close()

        return {

            "error":

                "Block not found"

        }

    block = dict(block)

    conn.close()

    original_duration = float(

        block[
            "duration_hours"
        ]

    )

    delayed_duration = max(

        0,

        original_duration

        -

        delay_hours

    )

    percentage_remaining = (

        delayed_duration

        /

        original_duration

        *

        100

        if original_duration > 0

        else 0

    )

    return {

        "block_code":

            block_code,

        "original_duration_hours":

            original_duration,

        "delay_hours":

            delay_hours,

        "remaining_duration_hours":

            round(

                delayed_duration,

                2

            ),

        "remaining_capacity_percent":

            round(

                percentage_remaining,

                1

            ),

        "impact":

            (

                "HIGH"

                if percentage_remaining < 50

                else

                "MEDIUM"

                if percentage_remaining < 80

                else

                "LOW"

            ),

        "recommendation":

            (

                "Re-optimize the block because "
                "more than half of the maintenance "
                "window is lost."

                if percentage_remaining < 50

                else

                "Review lower priority tasks and "
                "consider moving them to another block."

                if percentage_remaining < 80

                else

                "Minor delay. Existing plan may "
                "still be feasible."

            ),

    }


# ============================================================
# WHAT-IF WEATHER ANALYSIS
# ============================================================

def whatif_weather(
    block_code: str,
    weather: str
) -> Dict:
    """
    Simulate weather impact on a block.

    Weather options:

    - rain
    - heavy_rain
    - fog
    - heat
    - storm
    """

    weather = weather.lower().strip()

    weather_impacts = {

        "rain": {

            "risk": "MEDIUM",

            "productivity_reduction": 20,

            "recommendation":
                (
                    "Continue only with appropriate "
                    "safety precautions."
                ),

        },

        "heavy_rain": {

            "risk": "HIGH",

            "productivity_reduction": 50,

            "recommendation":
                (
                    "Consider postponing outdoor "
                    "maintenance activities."
                ),

        },

        "fog": {

            "risk": "MEDIUM",

            "productivity_reduction": 15,

            "recommendation":
                (
                    "Coordinate with traffic control "
                    "due to reduced visibility."
                ),

        },

        "heat": {

            "risk": "MEDIUM",

            "productivity_reduction": 20,

            "recommendation":
                (
                    "Provide worker rest periods "
                    "and monitor heat exposure."
                ),

        },

        "storm": {

            "risk": "CRITICAL",

            "productivity_reduction": 80,

            "recommendation":
                (
                    "Do not proceed until conditions "
                    "are declared safe."
                ),

        },

    }

    impact = weather_impacts.get(

        weather,

        {

            "risk": "UNKNOWN",

            "productivity_reduction": 0,

            "recommendation":

                "No weather rule available for "
                "the selected condition.",

        },

    )

    return {

        "block_code":

            block_code,

        "weather":

            weather,

        "risk":

            impact["risk"],

        "productivity_reduction_percent":

            impact[
                "productivity_reduction"
            ],

        "recommendation":

            impact[
                "recommendation"
            ],

    }
