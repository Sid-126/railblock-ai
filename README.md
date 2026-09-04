# RailBlock AI — Full Stack (Delhi–Ghaziabad)

AI-powered automatic block planning for Indian Railways (SIH26027 style).

## Features

1. **Train schedule → free gaps** — AI reads Delhi–Ghaziabad timetable and finds block windows  
2. **AI priority scores** — tasks ranked by criticality, urgency, impact, overdue  
3. **Resource check** — workers, rail crane, tower wagon, welding, supervisors  
4. **Role assignment** — SSE/JE, gangs, crane/tower operators by department  
5. **Officer approval** — Approve / Reject with comments  
6. **What-If** — delay impact & weather impact  
7. **SQLite database** — section Delhi–Ghaziabad  

## Quick start

```bash
cd railblock-full
pip install -r requirements.txt
cd backend
python seed.py          # creates data/railblock.db
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: **http://127.0.0.1:8000**

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/tasks | Prioritized tasks |
| GET | /api/schedule?day=Mon | Train timetable |
| GET | /api/gaps?day=Mon | AI free windows |
| POST | /api/optimize | Generate block proposals |
| GET | /api/blocks | Proposed/approved blocks |
| POST | /api/approve | Officer decision |
| POST | /api/whatif/delay | Delay simulation |
| POST | /api/whatif/weather | Weather simulation |
| GET | /api/resources?day=Mon | Resource availability |

## Demo flow

1. Login as **Section Controller** or **Sr. DEN**  
2. Open **Train Schedule** → see trains + AI gaps  
3. Click **Run AI Optimizer**  
4. Open **AI Optimizer** → see blocks, resource READY/SHORTAGE, roles  
5. **Officer Approval** → Approve / Reject  
6. **What-If** → delay or weather  

## Note on live train data

Timetable is stored in SQLite (realistic mock for Delhi–Ghaziabad).  
The same module can later consume live COA/NTES-style feeds without changing AI logic.

## Project layout

```
railblock-full/
├── backend/
│   ├── main.py          # FastAPI
│   ├── database.py
│   ├── seed.py
│   └── ai_engine.py     # priority, gaps, resources, what-if
├── frontend/
│   ├── index.html
│   └── js/app.js
├── data/
│   └── railblock.db     # created by seed.py
└── requirements.txt
```
