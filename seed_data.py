"""
Demo Data Seeder for Campus Voice
Populates realistic student feedback, issues, suggestions, and appreciations
spanning diverse departments, categories, locations, and SLA statuses.
"""

import os
import sqlite3
from datetime import datetime, timedelta
import random

from database import add_submission, get_connection, initialize_database
from category import department_for_category
from analyzer import analyze_emotion, analyze_feedback, extract_keyphrases
from priority import calculate_priority, calculate_severity, calculate_sla_deadline

DEMO_SAMPLES = [
    {
        "type": "Issue",
        "category": "Infrastructure",
        "location": "Academic Block",
        "frequency": "Daily",
        "outcome": "Replace or repair projector bulbs in Room 302.",
        "description": "The ceiling projector in classroom 302 keeps flickering and shuts down after 10 minutes of lecture. Faculty cannot display slides properly.",
        "anonymous": False,
        "student_name": "Aarav Sharma",
        "status": "In Progress",
        "upvotes": 7,
        "days_ago": 2
    },
    {
        "type": "Issue",
        "category": "Internet & Technology",
        "location": "Computer Lab",
        "frequency": "Several times a week",
        "outcome": "Reconfigure Wi-Fi access points and DHCP in Lab 2.",
        "description": "Wi-Fi in computer lab 2 is completely unavailable during afternoon practicals. The connection drops continuously and students cannot submit coding assignments.",
        "anonymous": True,
        "student_name": None,
        "status": "New",
        "upvotes": 12,
        "days_ago": 1
    },
    {
        "type": "Issue",
        "category": "Cleanliness",
        "location": "Washrooms",
        "frequency": "Daily",
        "outcome": "Deep clean and ensure running water on 2nd floor.",
        "description": "The 2nd floor washroom in B-Block is extremely dirty and has an unbearable foul smell. The flush valves are leaking and water is pooling on the tiles.",
        "anonymous": True,
        "student_name": None,
        "status": "Reviewing",
        "upvotes": 15,
        "days_ago": 3
    },
    {
        "type": "Issue",
        "category": "Safety",
        "location": "Parking",
        "frequency": "Ongoing",
        "outcome": "Install functional lighting and CCTV near bike parking.",
        "description": "Exposed electrical wiring near the two-wheeler parking lot right next to the puddle. This is a severe electric shock hazard during rain.",
        "anonymous": False,
        "student_name": "Rohan Verma",
        "status": "Resolved",
        "resolution_note": "Electrician deployed on emergency call. Insulated wiring and shifted junction box inside weather-proof enclosure.",
        "upvotes": 19,
        "days_ago": 5
    },
    {
        "type": "Suggestion",
        "category": "Canteen",
        "location": "Canteen",
        "frequency": "Daily",
        "outcome": "Introduce subsidized healthy meal combo options.",
        "description": "Introduce more fresh fruit, salads, and affordable nutritious breakfast options in the main dining hall instead of only oily deep-fried snacks.",
        "anonymous": False,
        "student_name": "Ananya Patel",
        "status": "Planned",
        "resolution_note": "Canteen Committee approved trial of seasonal fruit bowls and oats starting next Monday.",
        "upvotes": 28,
        "days_ago": 6
    },
    {
        "type": "Suggestion",
        "category": "Library",
        "location": "Library",
        "frequency": "Weekly",
        "outcome": "Extend reading hall timings till 10 PM during exam months.",
        "description": "Requesting extended study hours in the central library reading hall during internal examinations and end-semester finals.",
        "anonymous": True,
        "student_name": None,
        "status": "Implemented",
        "resolution_note": "Dean approved extended reading room hours from 8 AM to 10 PM throughout exam weeks.",
        "upvotes": 42,
        "days_ago": 10
    },
    {
        "type": "Appreciation",
        "category": "Transport",
        "location": "Transport / Bus",
        "frequency": "Daily",
        "outcome": "Express gratitude to driver Mr. Ramesh.",
        "description": "Appreciation for Bus Route 14 driver Mr. Ramesh who waited patiently for students during heavy rain and ensured everyone reached campus safely and punctually.",
        "anonymous": False,
        "student_name": "Pooja Hegde",
        "status": "Acknowledged",
        "resolution_note": "Formal letter of commendation issued by Transport In-charge.",
        "upvotes": 14,
        "days_ago": 4
    },
    {
        "type": "Issue",
        "category": "Infrastructure",
        "location": "Hostel",
        "frequency": "Daily",
        "outcome": "Fix drinking water cooler refrigeration unit in Hostel Block C.",
        "description": "The drinking water cooler on the ground floor of Hostel Block C is dispensing warm water and making loud grinding noises.",
        "anonymous": False,
        "student_name": "Vikram Singh",
        "status": "Resolved",
        "resolution_note": "Compressor replaced and filter cartridges changed by maintenance contractor.",
        "upvotes": 8,
        "days_ago": 7
    }
]


def seed_database():
    initialize_database()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM submissions").fetchone()["c"]
    conn.close()

    print(f"Current submissions in database: {count}")
    print("Seeding realistic sample data...")

    for sample in DEMO_SAMPLES:
        desc = sample["description"]
        cat = sample["category"]
        stype = sample["type"]
        dept = department_for_category(cat)
        sentiment = analyze_feedback(desc)
        emotion = analyze_emotion(desc, stype)
        tags = extract_keyphrases(desc)
        severity = calculate_severity(stype, desc)
        priority = calculate_priority(stype, severity, report_count=1, text=desc, upvote_count=sample.get("upvotes", 0))
        created_time = datetime.utcnow() - timedelta(days=sample["days_ago"], hours=random.randint(1, 10))
        sla_deadline = calculate_sla_deadline(priority, created_time)

        sub_id, code = add_submission(
            submission_type=stype,
            student_name=sample["student_name"],
            anonymous=sample["anonymous"],
            category=cat,
            location=sample["location"],
            frequency=sample["frequency"],
            desired_outcome=sample["outcome"],
            description=desc,
            image_filename=None,
            sentiment=sentiment,
            severity=severity,
            priority=priority,
            priority_reason="Seeded sample demonstration record.",
            department=dept,
            emotion=emotion,
            tags=tags,
            sla_deadline=sla_deadline
        )

        conn = get_connection()
        updated_time = created_time + timedelta(hours=random.randint(4, 28)) if sample["status"] in {"Resolved", "Implemented"} else created_time
        conn.execute("""
            UPDATE submissions 
            SET status = ?, resolution_note = ?, upvotes = ?, created_at = ?, updated_at = ?
            WHERE id = ?
        """, (
            sample["status"],
            sample.get("resolution_note"),
            sample.get("upvotes", 0),
            created_time.strftime("%Y-%m-%d %H:%M:%S"),
            updated_time.strftime("%Y-%m-%d %H:%M:%S"),
            sub_id
        ))
        conn.commit()
        conn.close()
        print(f"  + Added [{code}] {cat} -> {dept} ({sample['status']})")

    print("Data seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
