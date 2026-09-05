```python
"""
RailBlock AI - Seed Database

Creates realistic prototype data for:
Delhi – Ghaziabad Railway Section
"""

from database import get_conn, init_db


def seed():

    # ========================================================
    # RESET AND CREATE DATABASE
    # ========================================================

    init_db()

    conn = get_conn()
    c = conn.cursor()

    # ========================================================
    # USERS / OFFICERS
    # ========================================================

    users = [
        (
            1,
            "Section Controller",
            "Section Controller",
            "Control Office",
            "SC",
            "Northern Railway",
        ),
        (
            2,
            "SSE (P.Way)",
            "SSE (P.Way)",
            "Engineering",
            "PW",
            "Northern Railway",
        ),
        (
            3,
            "SSE (Signal)",
            "SSE (Signal)",
            "S&T",
            "ST",
            "Northern Railway",
        ),
        (
            4,
            "SSE (TRD)",
            "SSE (TRD)",
            "Traction",
            "TR",
            "Northern Railway",
        ),
        (
            5,
            "Sr. DEN",
            "Sr. DEN",
            "Divisional",
            "DN",
            "Delhi Division",
        ),
    ]

    c.executemany(
        """
        INSERT INTO users
        (id, name, role, department, initials, zone)

        VALUES (?, ?, ?, ?, ?, ?)
        """,
        users,
    )

    # ========================================================
    # RAILWAY SECTION
    # ========================================================

    c.execute(
        """
        INSERT INTO sections
        (id, name, corridor, length_km)

        VALUES (?, ?, ?, ?)
        """,
        (
            1,
            "Delhi–Ghaziabad",
            "Delhi Division – Northern Railway",
            20.5,
        ),
    )

    # ========================================================
    # TRAIN SCHEDULE
    # ========================================================

    # Prototype schedule.
    #
    # departure_time and arrival_time represent the time
    # during which a train occupies / affects the section.

    train_template = [

        # Morning peak

        (
            "12055",
            "Dehradun Jan Shatabdi",
            "UP",
            "06:15",
            "06:45",
            "Passenger",
        ),

        (
            "12401",
            "Magadh Express",
            "UP",
            "07:05",
            "07:35",
            "Passenger",
        ),

        (
            "14041",
            "Mussoorie Express",
            "DN",
            "08:20",
            "08:50",
            "Passenger",
        ),

        (
            "19019",
            "Dehradun Express",
            "UP",
            "09:10",
            "09:40",
            "Passenger",
        ),

        # Afternoon

        (
            "14229",
            "Yog Nagari Rishikesh",
            "UP",
            "15:40",
            "16:10",
            "Passenger",
        ),

        # Evening peak

        (
            "12056",
            "New Delhi Jan Shatabdi",
            "DN",
            "17:50",
            "18:20",
            "Passenger",
        ),

        (
            "14042",
            "Mussoorie Express",
            "UP",
            "19:30",
            "20:00",
            "Passenger",
        ),

        # Freight

        (
            "GOODS-02",
            "Freight Container",
            "DN",
            "21:00",
            "21:45",
            "Goods",
        ),

        # Night

        (
            "12402",
            "Magadh Express",
            "DN",
            "22:40",
            "23:10",
            "Passenger",
        ),
    ]


    train_id = 1

    # Insert Monday to Saturday schedule.

    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:

        for train in train_template:

            train_no = train[0]
            train_name = train[1]
            direction = train[2]
            departure_time = train[3]
            arrival_time = train[4]
            train_type = train[5]

            c.execute(
                """
                INSERT INTO train_schedule
                (
                    id,
                    section_id,
                    train_no,
                    train_name,
                    direction,
                    day_of_week,
                    departure_time,
                    arrival_time,
                    train_type
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    train_id,
                    1,
                    train_no,
                    train_name,
                    direction,
                    day,
                    departure_time,
                    arrival_time,
                    train_type,
                ),
            )

            train_id += 1


    # ========================================================
    # SUNDAY SCHEDULE
    # ========================================================

    # Sunday has fewer trains.
    # This creates more maintenance opportunities.

    sunday_trains = [

        (
            "12055",
            "Dehradun Jan Shatabdi",
            "UP",
            "06:15",
            "06:45",
            "Passenger",
        ),

        (
            "19019",
            "Dehradun Express",
            "UP",
            "09:10",
            "09:40",
            "Passenger",
        ),

        (
            "12056",
            "New Delhi Jan Shatabdi",
            "DN",
            "17:50",
            "18:20",
            "Passenger",
        ),

        (
            "14042",
            "Mussoorie Express",
            "UP",
            "19:30",
            "20:00",
            "Passenger",
        ),
    ]


    for train in sunday_trains:

        train_no = train[0]
        train_name = train[1]
        direction = train[2]
        departure_time = train[3]
        arrival_time = train[4]
        train_type = train[5]

        c.execute(
            """
            INSERT INTO train_schedule
            (
                id,
                section_id,
                train_no,
                train_name,
                direction,
                day_of_week,
                departure_time,
                arrival_time,
                train_type
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                train_id,
                1,
                train_no,
                train_name,
                direction,
                "Sun",
                departure_time,
                arrival_time,
                train_type,
            ),
        )

        train_id += 1


    # ========================================================
    # MAINTENANCE TASKS
    # ========================================================

    # Each task contains OPERATIONAL INPUTS.
    #
    # The algorithm will later calculate:
    #
    # Criticality
    # Urgency
    # Impact
    #
    # Values are from 0 to 100.


    tasks = [

        # ====================================================
        # ENGINEERING TASKS
        # ====================================================

        (
            "ENG-2401",
            "Rail fracture repair – KM 112.4",
            "Engineering",

            # Criticality Inputs
            95,     # fault_severity
            98,     # safety_risk
            90,     # asset_importance

            # Urgency Inputs
            90,     # deterioration_rate
            95,     # response_deadline
            98,     # safety_escalation

            # Impact Inputs
            85,     # trains_affected
            90,     # route_importance
            95,     # operational_disruption

            # Work Requirements
            4.5,    # est_hours
            6,      # overdue_days
            8,      # required_workers

            # Special Resources
            1,      # requires_crane
            0,      # requires_tower_wagon
            1,      # requires_welding
        ),

        (
            "ENG-2402",
            "Track geometry correction (twist)",
            "Engineering",

            75,
            80,
            75,

            70,
            75,
            80,

            65,
            80,
            70,

            3.0,
            2,
            6,

            0,
            0,
            0,
        ),

        (
            "ENG-2403",
            "Ballast cleaning and packing",
            "Engineering",

            45,
            40,
            60,

            35,
            40,
            40,

            40,
            65,
            45,

            6.0,
            0,
            10,

            0,
            0,
            0,
        ),

        (
            "ENG-2404",
            "Point and crossing renewal",
            "Engineering",

            90,
            85,
            90,

            80,
            85,
            85,

            90,
            95,
            90,

            5.5,
            4,
            8,

            1,
            0,
            1,
        ),

        (
            "ENG-2406",
            "LWR destressing",
            "Engineering",

            70,
            75,
            80,

            75,
            70,
            75,

            75,
            85,
            75,

            5.0,
            2,
            8,

            0,
            0,
            1,
        ),


        # ====================================================
        # SIGNAL AND TELECOMMUNICATION TASKS
        # ====================================================

        (
            "SNT-1108",
            "Signal aspect failure – Home signal",
            "S&T",

            95,
            98,
            95,

            95,
            98,
            98,

            90,
            95,
            95,

            2.0,
            3,
            3,

            0,
            0,
            0,
        ),

        (
            "SNT-1109",
            "Axle counter reset and calibration",
            "S&T",

            70,
            80,
            85,

            70,
            75,
            75,

            75,
            90,
            70,

            1.5,
            2,
            2,

            0,
            0,
            0,
        ),

        (
            "SNT-1111",
            "Level crossing interlocking check",
            "S&T",

            85,
            90,
            85,

            85,
            80,
            90,

            80,
            85,
            80,

            2.5,
            5,
            4,

            0,
            0,
            0,
        ),

        (
            "SNT-1114",
            "Track circuit bonding repair",
            "S&T",

            92,
            95,
            90,

            90,
            92,
            95,

            85,
            90,
            90,

            1.5,
            5,
            3,

            0,
            0,
            0,
        ),


        # ====================================================
        # TRACTION / OHE TASKS
        # ====================================================

        (
            "TRD-3301",
            "OHE dropper failure repair",
            "Traction",

            90,
            95,
            90,

            85,
            90,
            95,

            85,
            90,
            85,

            3.0,
            4,
            5,

            0,
            1,
            0,
        ),

        (
            "TRD-3302",
            "Insulator cleaning and replacement",
            "Traction",

            60,
            55,
            70,

            55,
            60,
            60,

            65,
            80,
            60,

            4.0,
            1,
            4,

            0,
            1,
            0,
        ),

        (
            "TRD-3304",
            "ATD (Auto Tensioning Device) check",
            "Traction",

            75,
            80,
            85,

            75,
            80,
            80,

            80,
            85,
            75,

            2.0,
            3,
            3,

            0,
            1,
            0,
        ),
    ]


    # ========================================================
    # INSERT TASKS
    # ========================================================

    for task_id, task in enumerate(tasks, start=1):

        c.execute(
            """
            INSERT INTO tasks
            (
                id,

                task_code,
                description,
                department,
                section_id,

                ------------------------------------------------
                -- CRITICALITY INPUTS
                ------------------------------------------------

                fault_severity,
                safety_risk,
                asset_importance,

                ------------------------------------------------
                -- URGENCY INPUTS
                ------------------------------------------------

                deterioration_rate,
                response_deadline,
                safety_escalation,

                ------------------------------------------------
                -- IMPACT INPUTS
                ------------------------------------------------

                trains_affected,
                route_importance,
                operational_disruption,

                ------------------------------------------------
                -- WORK REQUIREMENTS
                ------------------------------------------------

                est_hours,
                overdue_days,
                required_workers,

                ------------------------------------------------
                -- SPECIAL RESOURCES
                ------------------------------------------------

                requires_crane,
                requires_tower_wagon,
                requires_welding
            )

            VALUES
            (
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """,

            (
                task_id,

                task[0],
                task[1],
                task[2],
                1,

                # Criticality Inputs
                task[3],
                task[4],
                task[5],

                # Urgency Inputs
                task[6],
                task[7],
                task[8],

                # Impact Inputs
                task[9],
                task[10],
                task[11],

                # Work Requirements
                task[12],
                task[13],
                task[14],

                # Resources
                task[15],
                task[16],
                task[17],
            ),
        )


    # ========================================================
    # RESOURCES
    # ========================================================

    resources = [

        (
            1,
            "P.Way Gang A",
            "workers",
            "Engineering",
            "Track maintenance",
            12,
        ),

        (
            2,
            "P.Way Gang B",
            "workers",
            "Engineering",
            "Track maintenance",
            10,
        ),

        (
            3,
            "Signal Maintainer Team",
            "workers",
            "S&T",
            "Signalling",
            6,
        ),

        (
            4,
            "TRD Gang",
            "workers",
            "Traction",
            "OHE maintenance",
            8,
        ),

        (
            5,
            "Rail Crane-01",
            "crane",
            "Engineering",
            "Heavy lifting",
            1,
        ),

        (
            6,
            "Tower Wagon-01",
            "tower_wagon",
            "Traction",
            "OHE access",
            1,
        ),

        (
            7,
            "Welding Unit",
            "welding",
            "Engineering",
            "Rail welding",
            2,
        ),

        (
            8,
            "JE/SSE Pool",
            "supervisor",
            "All",
            "Maintenance supervision",
            5,
        ),
    ]


    c.executemany(
        """
        INSERT INTO resources
        (
            id,
            name,
            resource_type,
            department,
            skill,
            total_count
        )

        VALUES (?, ?, ?, ?, ?, ?)
        """,
        resources,
    )


    # ========================================================
    # RESOURCE AVAILABILITY
    # ========================================================

    days = [

        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    ]


    for day in days:


        # ----------------------------------------------------
        # WORKERS AND COMMON RESOURCES
        # ----------------------------------------------------

        normal_resources = [

            (1, 12),
            (2, 10),
            (3, 6),
            (4, 8),
            (7, 2),
            (8, 5),
        ]


        for resource_id, total in normal_resources:

            # Sunday availability is reduced.

            if day == "Sun":

                available = max(
                    1,
                    total // 2
                )

            else:

                available = total


            c.execute(
                """
                INSERT INTO resource_availability
                (
                    resource_id,
                    day_of_week,
                    shift,
                    available_count
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    resource_id,
                    day,
                    "day",
                    available,
                ),
            )


        # ----------------------------------------------------
        # CRANE AVAILABILITY
        # ----------------------------------------------------

        # Crane is only available:
        #
        # Tuesday
        # Thursday
        # Saturday

        crane_available = (

            1

            if day in [
                "Tue",
                "Thu",
                "Sat",
            ]

            else 0
        )


        c.execute(
            """
            INSERT INTO resource_availability
            (
                resource_id,
                day_of_week,
                shift,
                available_count
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                5,
                day,
                "day",
                crane_available,
            ),
        )


        # ----------------------------------------------------
        # TOWER WAGON AVAILABILITY
        # ----------------------------------------------------

        # Tower wagon is unavailable Wednesday.

        tower_wagon_available = (

            0

            if day == "Wed"

            else 1
        )


        c.execute(
            """
            INSERT INTO resource_availability
            (
                resource_id,
                day_of_week,
                shift,
                available_count
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                6,
                day,
                "day",
                tower_wagon_available,
            ),
        )


    # ========================================================
    # SAVE DATABASE
    # ========================================================

    conn.commit()

    conn.close()

    print()

    print(
        "========================================"
    )

    print(
        "RailBlock AI seed data loaded successfully"
    )

    print(
        "Section: Delhi–Ghaziabad"
    )

    print(
        f"Tasks inserted: {len(tasks)}"
    )

    print(
        "========================================"
    )


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    seed()
```
