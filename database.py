import os
import sqlite3
import secrets
import string
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "data", "campus_voice.db")


def get_connection():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _code():
    alphabet = string.ascii_uppercase + string.digits
    return "CV-" + "".join(secrets.choice(alphabet) for _ in range(8))


def initialize_database():
    connection = get_connection()
    connection.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_code TEXT,
            submission_type TEXT NOT NULL,
            student_name TEXT,
            anonymous INTEGER NOT NULL DEFAULT 0,
            category TEXT NOT NULL,
            location TEXT,
            frequency TEXT,
            desired_outcome TEXT,
            description TEXT NOT NULL,
            image_filename TEXT,
            sentiment TEXT NOT NULL DEFAULT 'Neutral',
            severity TEXT NOT NULL DEFAULT 'None',
            priority TEXT NOT NULL DEFAULT 'None',
            priority_reason TEXT,
            status TEXT NOT NULL DEFAULT 'New',
            admin_notes TEXT,
            resolution_note TEXT,
            department TEXT,
            upvotes INTEGER NOT NULL DEFAULT 0,
            sla_deadline TIMESTAMP,
            emotion TEXT NOT NULL DEFAULT 'Neutral',
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    columns = {row["name"] for row in connection.execute("PRAGMA table_info(submissions)").fetchall()}
    migrations = {
        "public_code": "ALTER TABLE submissions ADD COLUMN public_code TEXT",
        "frequency": "ALTER TABLE submissions ADD COLUMN frequency TEXT",
        "desired_outcome": "ALTER TABLE submissions ADD COLUMN desired_outcome TEXT",
        "priority_reason": "ALTER TABLE submissions ADD COLUMN priority_reason TEXT",
        "admin_notes": "ALTER TABLE submissions ADD COLUMN admin_notes TEXT",
        "resolution_note": "ALTER TABLE submissions ADD COLUMN resolution_note TEXT",
        "updated_at": "ALTER TABLE submissions ADD COLUMN updated_at TIMESTAMP",
        "sentiment": "ALTER TABLE submissions ADD COLUMN sentiment TEXT NOT NULL DEFAULT 'Neutral'",
        "severity": "ALTER TABLE submissions ADD COLUMN severity TEXT NOT NULL DEFAULT 'None'",
        "priority": "ALTER TABLE submissions ADD COLUMN priority TEXT NOT NULL DEFAULT 'None'",
        "status": "ALTER TABLE submissions ADD COLUMN status TEXT NOT NULL DEFAULT 'New'",
        "image_filename": "ALTER TABLE submissions ADD COLUMN image_filename TEXT",
        "department": "ALTER TABLE submissions ADD COLUMN department TEXT",
        "upvotes": "ALTER TABLE submissions ADD COLUMN upvotes INTEGER NOT NULL DEFAULT 0",
        "sla_deadline": "ALTER TABLE submissions ADD COLUMN sla_deadline TIMESTAMP",
        "emotion": "ALTER TABLE submissions ADD COLUMN emotion TEXT NOT NULL DEFAULT 'Neutral'",
        "tags": "ALTER TABLE submissions ADD COLUMN tags TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)

    rows = connection.execute("SELECT id, created_at, updated_at, public_code, category, department, priority FROM submissions").fetchall()
    from category import department_for_category
    from priority import calculate_sla_deadline
    for row in rows:
        code = row["public_code"] or _code()
        dept = row["department"] or department_for_category(row["category"] or "General")
        deadline = calculate_sla_deadline(row["priority"] or "None", row["created_at"])
        connection.execute(
            """UPDATE submissions 
               SET public_code = ?, 
                   updated_at = COALESCE(updated_at, created_at),
                   department = COALESCE(department, ?),
                   sla_deadline = COALESCE(sla_deadline, ?)
               WHERE id = ?""",
            (code, dept, deadline, row["id"]),
        )

    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_submissions_public_code ON submissions(public_code)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submissions_type ON submissions(submission_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions(created_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submissions_category ON submissions(category)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_submissions_department ON submissions(department)")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS submission_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(submission_id) REFERENCES submissions(id) ON DELETE CASCADE
        )
    """)
    existing_events = connection.execute("SELECT COUNT(*) AS c FROM submission_events").fetchone()["c"]
    if existing_events == 0:
        connection.execute("""
            INSERT INTO submission_events (submission_id, event_type, to_status, note, created_at)
            SELECT id, 'created', status, 'Submission received', created_at
            FROM submissions
        """)

    connection.commit()
    connection.close()


def add_submission(submission_type, student_name, anonymous, category, location, frequency,
                   desired_outcome, description, image_filename, sentiment, severity, priority,
                   priority_reason, department=None, emotion="Neutral", tags=None, sla_deadline=None):
    from category import department_for_category
    from priority import calculate_sla_deadline

    if not department:
        department = department_for_category(category)
    if not sla_deadline:
        sla_deadline = calculate_sla_deadline(priority)
    if isinstance(tags, (list, tuple)):
        tags = json.dumps(tags)

    connection = get_connection()
    public_code = _code()
    while connection.execute("SELECT 1 FROM submissions WHERE public_code = ?", (public_code,)).fetchone():
        public_code = _code()

    cursor = connection.execute("""
        INSERT INTO submissions (
            public_code, submission_type, student_name, anonymous, category, location,
            frequency, desired_outcome, description, image_filename, sentiment, severity,
            priority, priority_reason, status, department, emotion, tags, sla_deadline, upvotes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        public_code, submission_type, student_name, int(anonymous), category, location,
        frequency, desired_outcome, description, image_filename, sentiment, severity,
        priority, priority_reason, "New", department, emotion, tags, sla_deadline
    ))
    submission_id = cursor.lastrowid
    connection.execute(
        "INSERT INTO submission_events (submission_id, event_type, to_status, note) VALUES (?, 'created', 'New', 'Submission received')",
        (submission_id,),
    )
    connection.commit()
    connection.close()
    return submission_id, public_code


def get_submission(submission_id):
    connection = get_connection()
    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    connection.close()
    return dict(row) if row else None


def get_submission_by_code(public_code):
    connection = get_connection()
    row = connection.execute("SELECT * FROM submissions WHERE UPPER(public_code) = UPPER(?)", (public_code.strip(),)).fetchone()
    connection.close()
    return dict(row) if row else None


def increment_upvote(public_code):
    """Increment student confirmation/upvote counter for community signal."""
    connection = get_connection()
    row = connection.execute("SELECT id, upvotes FROM submissions WHERE UPPER(public_code) = UPPER(?)", (public_code.strip(),)).fetchone()
    if not row:
        connection.close()
        return None
    new_count = (row["upvotes"] or 0) + 1
    connection.execute("UPDATE submissions SET upvotes = ? WHERE id = ?", (new_count, row["id"]))
    connection.execute("INSERT INTO submission_events (submission_id, event_type, note) VALUES (?, 'upvote', 'Student confirmation added')", (row["id"],))
    connection.commit()
    connection.close()
    return new_count


def update_department(submission_id, department):
    """Assign or re-route submission to a campus department/unit."""
    connection = get_connection()
    connection.execute("UPDATE submissions SET department = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (department, submission_id))
    connection.execute("INSERT INTO submission_events (submission_id, event_type, note) VALUES (?, 'reassignment', ?)", 
                       (submission_id, f"Routed to {department}"))
    connection.commit()
    connection.close()
    return True


def get_status_history(submission_id):
    connection = get_connection()
    rows = connection.execute("""
        SELECT event_type, from_status, to_status, note, created_at
        FROM submission_events
        WHERE submission_id = ?
        ORDER BY datetime(created_at) ASC, id ASC
    """, (submission_id,)).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_submissions(submission_type="All", category="All", priority="All", status="All", department="All", search="", date_range="All"):
    connection = get_connection()
    query = "SELECT * FROM submissions WHERE 1 = 1"
    values = []
    if submission_type != "All":
        query += " AND submission_type = ?"; values.append(submission_type)
    if category != "All":
        query += " AND category = ?"; values.append(category)
    if priority != "All":
        query += " AND priority = ?"; values.append(priority)
    if status != "All":
        query += " AND status = ?"; values.append(status)
    if department != "All":
        query += " AND department = ?"; values.append(department)
    if date_range in {"7d", "30d", "90d"}:
        days = int(date_range[:-1])
        query += f" AND datetime(created_at) >= datetime('now', '-{days} days')"
    if search:
        query += " AND (description LIKE ? OR category LIKE ? OR location LIKE ? OR public_code LIKE ? OR desired_outcome LIKE ? OR department LIKE ?)"
        term = f"%{search}%"; values.extend([term] * 6)
    query += """
        ORDER BY CASE
            WHEN submission_type = 'Issue' AND priority = 'High' AND status != 'Resolved' THEN 1
            WHEN submission_type = 'Issue' AND priority = 'Medium' AND status != 'Resolved' THEN 2
            WHEN submission_type = 'Issue' AND priority = 'Low' AND status != 'Resolved' THEN 3
            WHEN status = 'New' THEN 4
            ELSE 5 END,
            datetime(created_at) DESC, id DESC
    """
    rows = connection.execute(query, values).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def update_status(submission_id, status, note=""):
    connection = get_connection()
    row = connection.execute("SELECT status FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    if not row:
        connection.close()
        return False
    old_status = row["status"]
    connection.execute("""
        UPDATE submissions SET status = ?, updated_at = CURRENT_TIMESTAMP,
        resolution_note = CASE
            WHEN ? = 'Resolved' THEN CASE WHEN TRIM(?) != '' THEN ? ELSE resolution_note END
            WHEN ? != 'Resolved' THEN NULL
            ELSE resolution_note
        END
        WHERE id = ?
    """, (status, status, note, note, status, submission_id))
    if old_status != status or note.strip():
        connection.execute("""
            INSERT INTO submission_events (submission_id, event_type, from_status, to_status, note)
            VALUES (?, 'status_change', ?, ?, ?)
        """, (submission_id, old_status, status, note.strip() or None))
    connection.commit()
    connection.close()
    return True


def update_admin_notes(submission_id, notes):
    connection = get_connection()
    connection.execute("UPDATE submissions SET admin_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (notes.strip(), submission_id))
    connection.execute("INSERT INTO submission_events (submission_id, event_type, note) VALUES (?, 'note', ?)", (submission_id, 'Internal note updated'))
    connection.commit()
    connection.close()


def update_analysis(submission_id, sentiment, severity, priority, priority_reason=None):
    connection = get_connection()
    connection.execute("""
        UPDATE submissions
        SET sentiment=?, severity=?, priority=?, priority_reason=?
        WHERE id=?
          AND (COALESCE(sentiment, '') != COALESCE(?, '')
            OR COALESCE(severity, '') != COALESCE(?, '')
            OR COALESCE(priority, '') != COALESCE(?, '')
            OR COALESCE(priority_reason, '') != COALESCE(?, ''))
    """, (sentiment, severity, priority, priority_reason, submission_id, sentiment, severity, priority, priority_reason))
    connection.commit()
    connection.close()


def get_categories():
    connection = get_connection()
    rows = connection.execute("SELECT DISTINCT category FROM submissions WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category").fetchall()
    connection.close()
    return [row["category"] for row in rows]


def get_departments():
    connection = get_connection()
    rows = connection.execute("SELECT DISTINCT department FROM submissions WHERE department IS NOT NULL AND TRIM(department) != '' ORDER BY department").fetchall()
    connection.close()
    return [row["department"] for row in rows]


def get_public_board(limit=40):
    """Safe, sanitized public campus feed showing resolved fixes and active campus improvements."""
    connection = get_connection()
    rows = connection.execute("""
        SELECT public_code, submission_type, category, location, description, status,
               resolution_note, upvotes, department, created_at, updated_at
        FROM submissions
        WHERE status IN ('Resolved', 'In Progress', 'Implemented', 'Planned')
        ORDER BY CASE WHEN status IN ('Resolved', 'Implemented') THEN 1 ELSE 2 END,
                 datetime(updated_at) DESC
        LIMIT ?
    """, (limit,)).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_executive_summary():
    """Generates structured high-level analytics for campus administration and accreditation reviews."""
    connection = get_connection()
    total = connection.execute("SELECT COUNT(*) AS c FROM submissions").fetchone()["c"]
    by_type = dict(connection.execute("SELECT submission_type, COUNT(*) FROM submissions GROUP BY submission_type").fetchall())
    by_status = dict(connection.execute("SELECT status, COUNT(*) FROM submissions GROUP BY status").fetchall())
    by_dept = connection.execute("""
        SELECT 
            COALESCE(department, 'Unassigned') as dept,
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('Resolved', 'Implemented') THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN status NOT IN ('Resolved', 'Implemented', 'Declined') THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN priority = 'High' AND status NOT IN ('Resolved', 'Implemented') THEN 1 ELSE 0 END) as high_open
        FROM submissions
        GROUP BY department
        ORDER BY total DESC
    """).fetchall()

    sentiment_counts = dict(connection.execute("SELECT sentiment, COUNT(*) FROM submissions GROUP BY sentiment").fetchall())
    emotion_counts = dict(connection.execute("SELECT COALESCE(emotion, 'Neutral'), COUNT(*) FROM submissions GROUP BY emotion").fetchall())

    # SLA Compliance rate
    resolved_rows = connection.execute("""
        SELECT s.created_at, s.updated_at, s.sla_deadline, s.priority
        FROM submissions s
        WHERE s.status IN ('Resolved', 'Implemented')
    """).fetchall()

    on_time = 0
    overdue = 0
    for r in resolved_rows:
        if r["sla_deadline"] and r["updated_at"]:
            try:
                deadline = datetime.fromisoformat(str(r["sla_deadline"]).replace("Z", "").replace("+00:00", ""))
                resolved_time = datetime.fromisoformat(str(r["updated_at"]).replace("Z", "").replace("+00:00", ""))
                if resolved_time <= deadline:
                    on_time += 1
                else:
                    overdue += 1
            except Exception:
                on_time += 1
        else:
            on_time += 1

    total_resolved = len(resolved_rows)
    sla_compliance = round((on_time / total_resolved * 100), 1) if total_resolved > 0 else 100.0

    connection.close()
    return {
        "total_submissions": total,
        "by_type": by_type,
        "by_status": by_status,
        "departments": [dict(d) for d in by_dept],
        "sentiment": sentiment_counts,
        "emotion": emotion_counts,
        "sla_compliance_rate": sla_compliance,
        "resolved_count": total_resolved,
        "on_time_count": on_time,
        "overdue_count": overdue
    }
