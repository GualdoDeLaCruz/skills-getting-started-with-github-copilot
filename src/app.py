"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Database configuration
DATABASE_PATH = os.path.join(current_dir.parent, "activities.db")

# Initial activities data
INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    # Sports related activities
    "Soccer Team": {
        "description": "Join the school soccer team and compete in local leagues",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 18,
        "participants": ["lucas@mergington.edu", "mia@mergington.edu"]
    },
    "Basketball Club": {
        "description": "Practice basketball skills and play friendly matches",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["liam@mergington.edu", "ava@mergington.edu"]
    },
    # Artistic activities
    "Drama Club": {
        "description": "Participate in school plays and improve acting skills",
        "schedule": "Mondays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["noah@mergington.edu", "isabella@mergington.edu"]
    },
    "Art Workshop": {
        "description": "Explore painting, drawing, and other visual arts",
        "schedule": "Fridays, 2:00 PM - 3:30 PM",
        "max_participants": 16,
        "participants": ["amelia@mergington.edu", "benjamin@mergington.edu"]
    },
    # Intellectual activities
    "Math Olympiad": {
        "description": "Prepare for math competitions and solve challenging problems",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 10,
        "participants": ["charlotte@mergington.edu", "jack@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["harper@mergington.edu", "elijah@mergington.edu"]
    }
}


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with tables and initial data"""
    with get_db() as conn:
        # Create tables
        conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT,
            schedule TEXT,
            max_participants INTEGER
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            activity_name TEXT,
            email TEXT,
            PRIMARY KEY (activity_name, email),
            FOREIGN KEY (activity_name) REFERENCES activities(name)
        )
        """)

        # Check if we need to populate initial data
        cursor = conn.execute("SELECT COUNT(*) FROM activities")
        if cursor.fetchone()[0] == 0:
            # Populate initial data
            for name, details in INITIAL_ACTIVITIES.items():
                conn.execute(
                    "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                    (name, details["description"], details["schedule"], details["max_participants"])
                )
                # Add participants
                for email in details["participants"]:
                    conn.execute(
                        "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
                        (name, email)
                    )
            conn.commit()


# Initialize database on startup
init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    """Get all activities with their participants"""
    with get_db() as conn:
        activities = {}
        # Get all activities
        cursor = conn.execute("SELECT * FROM activities")
        for row in cursor:
            activities[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": []
            }

        # Get participants for each activity
        cursor = conn.execute("SELECT activity_name, email FROM participants")
        for row in cursor:
            activities[row["activity_name"]]["participants"].append(row["email"])

        return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_db() as conn:
        # Check if activity exists
        cursor = conn.execute("SELECT max_participants FROM activities WHERE name = ?", (activity_name,))
        activity = cursor.fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # Check current participants
        cursor = conn.execute("SELECT COUNT(*) FROM participants WHERE activity_name = ?", (activity_name,))
        current_participants = cursor.fetchone()[0]

        if current_participants >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        # Check if already registered
        cursor = conn.execute(
            "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Already registered for this activity")

        # Add participant
        conn.execute(
            "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
            (activity_name, email)
        )
        conn.commit()

        return {"message": f"Successfully signed up for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Remove a student from an activity"""
    with get_db() as conn:
        # Check if activity exists
        cursor = conn.execute("SELECT 1 FROM activities WHERE name = ?", (activity_name,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Activity not found")

        # Remove participant
        cursor = conn.execute(
            "DELETE FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Participant not found")

        conn.commit()
        return {"message": f"Successfully unregistered from {activity_name}"}
