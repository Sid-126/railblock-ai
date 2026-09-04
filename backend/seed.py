"""
Seed realistic data for Delhi – Ghaziabad section
"""
from database import get_conn, init_db


def seed():
    init_db()
    conn = get_conn()
    c = conn.cursor()

    # Users / Officers
    users = [
        (1, "Section Controller", "Section Controller", "Control Office", "SC", "Northern Railway"),
        (2, "SSE (P.Way)", "SSE (P.Way)", "Engineering", "PW", "Northern Railway"),
        (3, "SSE (Signal)", "SSE (Signal)", "S&T", "ST", "Northern Railway"),
        (4, "SSE (TRD)", "SSE (TRD)", "Traction", "TR", "Northern Railway"),
        (5, "Sr. DEN", "Sr. DEN", "Divisional", "DN", "Delhi Division"),
    ]
    c.executemany(
        "INSERT INTO users (id, name, role, department, initials, zone) VALUES (?,?,?,?,?,?)",
        users,
    )

    # Section
    c.execute(
        "INSERT INTO sections (id, name, corridor, length_km) VALUES (1, 'Delhi–Ghaziabad', 'Delhi Division – NR', 20.5)"
    )

    # Train schedule (one week sample – Delhi–Ghaziabad style)
    # day_of_week: Mon Tue Wed Thu Fri Sat Sun
    trains = [
        # Morning peak
        (1, 1, "12055", "Dehradun Jan Shatabdi", "UP", "Mon", "06:15", "06:45", "Passenger"),
        (2, 1, "12401", "Magadh Express", "UP", "Mon", "07:05", "07:35", "Passenger"),
        (3, 1, "14041", "Mussoorie Express", "DN", "Mon", "08:20", "08:50", "Passenger"),
        (4, 1, "19019", "Dehradun Express", "UP", "Mon", "09:10", "09:40", "Passenger"),
        # Mid-day gap opportunity ~10:00-13:00 partially
        (7, 1, "14229", "Yog Nagari Rishikesh", "UP", "Mon", "15:40", "16:10", "Passenger"),
        (8, 1, "12056", "New Delhi Jan Shatabdi", "DN", "Mon", "17:50", "18:20", "Passenger"),
        (9, 1, "14042", "Mussoorie Express", "UP", "Mon", "19:30", "20:00", "Passenger"),
        (10, 1, "GOODS-02", "Freight Container", "DN", "Mon", "21:00", "21:45", "Goods"),
        # Night quieter
        (11, 1, "12402", "Magadh Express", "DN", "Mon", "22:40", "23:10", "Passenger"),
    ]

    # Replicate similar pattern for Tue–Sat with slight variations, lighter on Sun
    base = list(trains)
    tid = 12
    for day in ["Tue", "Wed", "Thu", "Fri", "Sat"]:
        for t in base:
            c.execute(
                """INSERT INTO train_schedule
                (id, section_id, train_no, train_name, direction, day_of_week, departure_time, arrival_time, train_type)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (tid, t[1], t[2], t[3], t[4], day, t[6], t[7], t[8]),
            )
            tid += 1

    # Sunday lighter
    sunday = [
        (tid, 1, "12055", "Dehradun Jan Shatabdi", "UP", "Sun", "06:15", "06:45", "Passenger"),
        (tid + 1, 1, "19019", "Dehradun Express", "UP", "Sun", "09:10", "09:40", "Passenger"),
        (tid + 3, 1, "12056", "New Delhi Jan Shatabdi", "DN", "Sun", "17:50", "18:20", "Passenger"),
        (tid + 4, 1, "14042", "Mussoorie Express", "UP", "Sun", "19:30", "20:00", "Passenger"),
    ]
    for t in sunday:
        c.execute(
            """INSERT INTO train_schedule
            (id, section_id, train_no, train_name, direction, day_of_week, departure_time, arrival_time, train_type)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            t,
        )

    # Also insert Mon trains
    for t in base:
        c.execute(
            """INSERT INTO train_schedule
            (id, section_id, train_no, train_name, direction, day_of_week, departure_time, arrival_time, train_type)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            t,
        )

    # Tasks
    tasks = [
        ("ENG-2401", "Rail fracture repair – KM 112.4", "Engineering", 1, 95, 90, 85, 4.5, 6, 8, 1, 0, 1),
        ("ENG-2402", "Track geometry correction (twist)", "Engineering", 1, 70, 55, 60, 3.0, 2, 6, 0, 0, 0),
        ("ENG-2403", "Ballast cleaning & packing", "Engineering", 1, 45, 40, 35, 6.0, 0, 10, 0, 0, 0),
        ("ENG-2404", "Point & crossing renewal", "Engineering", 1, 80, 75, 90, 5.5, 4, 8, 1, 0, 1),
        ("SNT-1108", "Signal aspect failure – Home signal", "S&T", 1, 92, 95, 88, 2.0, 3, 3, 0, 0, 0),
        ("SNT-1109", "Axle counter reset & calibration", "S&T", 1, 75, 70, 65, 1.5, 2, 2, 0, 0, 0),
        ("SNT-1111", "Level crossing interlocking check", "S&T", 1, 85, 80, 70, 2.5, 5, 4, 0, 0, 0),
        ("TRD-3301", "OHE dropper failure repair", "Traction", 1, 88, 85, 80, 3.0, 4, 5, 0, 1, 0),
        ("TRD-3302", "Insulator cleaning & replacement", "Traction", 1, 65, 60, 55, 4.0, 1, 4, 0, 1, 0),
        ("TRD-3304", "ATD (Auto Tensioning Device) check", "Traction", 1, 78, 72, 75, 2.0, 3, 3, 0, 1, 0),
        ("ENG-2406", "LWR destressing", "Engineering", 1, 72, 65, 70, 5.0, 2, 8, 0, 0, 1),
        ("SNT-1114", "Track circuit bonding repair", "S&T", 1, 90, 88, 82, 1.5, 5, 3, 0, 0, 0),
    ]
    for i, t in enumerate(tasks, 1):
        c.execute(
            """INSERT INTO tasks
            (id, task_code, description, department, section_id, criticality, urgency, impact,
             est_hours, overdue_days, required_workers, requires_crane, requires_tower_wagon, requires_welding)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (i, *t),
        )

    # Resources
    resources = [
        (1, "P.Way Gang A", "workers", "Engineering", "Track maintenance", 12),
        (2, "P.Way Gang B", "workers", "Engineering", "Track maintenance", 10),
        (3, "Signal Maintainer Team", "workers", "S&T", "Signalling", 6),
        (4, "TRD Gang", "workers", "Traction", "OHE", 8),
        (5, "Rail Crane-01", "crane", "Engineering", "Heavy lift", 1),
        (6, "Tower Wagon-01", "tower_wagon", "Traction", "OHE access", 1),
        (7, "Welding Unit", "welding", "Engineering", "Rail welding", 2),
        (8, "JE/SSE Pool", "supervisor", "All", "Supervision", 5),
    ]
    c.executemany(
        "INSERT INTO resources (id, name, resource_type, department, skill, total_count) VALUES (?,?,?,?,?,?)",
        resources,
    )

    # Availability (simplified: most available Mon–Sat day shift; crane limited)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day in days:
        for rid, total in [(1, 12), (2, 10), (3, 6), (4, 8), (7, 2), (8, 5)]:
            avail = total if day != "Sun" else max(1, total // 2)
            c.execute(
                "INSERT INTO resource_availability (resource_id, day_of_week, shift, available_count) VALUES (?,?,?,?)",
                (rid, day, "day", avail),
            )
        # Crane: available Tue, Thu, Sat only in this mock
        crane_avail = 1 if day in ("Tue", "Thu", "Sat") else 0
        c.execute(
            "INSERT INTO resource_availability (resource_id, day_of_week, shift, available_count) VALUES (?,?,?,?)",
            (5, day, "day", crane_avail),
        )
        # Tower wagon: available most days except Wed
        tw = 0 if day == "Wed" else 1
        c.execute(
            "INSERT INTO resource_availability (resource_id, day_of_week, shift, available_count) VALUES (?,?,?,?)",
            (6, day, "day", tw),
        )

    conn.commit()
    conn.close()
    print("Seed data loaded for Delhi–Ghaziabad")


if __name__ == "__main__":
    seed()
