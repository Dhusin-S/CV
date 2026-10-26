"""
Automated Test Suite for Campus Voice Enterprise
Run with: python -m unittest test_app.py
"""

import json
import unittest
from app import app
from database import (
    add_submission, get_connection, get_executive_summary,
    get_public_board, get_submission_by_code, increment_upvote,
    initialize_database, update_department, update_status
)
from analyzer import (
    analyze_emotion, analyze_feedback, evaluate_content_quality, extract_keyphrases
)
from category import analyze_category, analyze_category_with_confidence, department_for_category
from priority import (
    calculate_priority, calculate_severity, calculate_sla_deadline, evaluate_sla_status
)
from issue_matcher import find_recent_similar


class TestIntelligenceRules(unittest.TestCase):
    def test_sentiment_analysis(self):
        self.assertEqual(analyze_feedback("The new library books and staff are amazing and helpful"), "Positive")
        self.assertEqual(analyze_feedback("The washrooms are dirty and the flush does not work"), "Negative")
        self.assertEqual(analyze_feedback("Classroom 101 lecture timetable schedule"), "Neutral")

    def test_emotion_analysis(self):
        self.assertEqual(analyze_emotion("This is the worst and completely horrible experience, totally useless", "Issue"), "Frustrated")
        self.assertEqual(analyze_emotion("There is a serious hazard with electric wires sparking", "Issue"), "Concerned")
        self.assertEqual(analyze_emotion("We should propose adding filtered water coolers near the library", "Suggestion"), "Constructive")
        self.assertEqual(analyze_emotion("Thank you so much to the security team for helping us today", "Appreciation"), "Appreciative")

    def test_keyphrase_extraction(self):
        text = "The drinking water cooler on the second floor has an electric shock risk"
        phrases = extract_keyphrases(text, max_phrases=3)
        self.assertTrue(len(phrases) >= 1)

    def test_category_and_department(self):
        cat_info = analyze_category_with_confidence("The wifi network in computer lab is down")
        self.assertEqual(cat_info["category"], "Internet & Technology")
        self.assertEqual(cat_info["department"], "IT & Systems Cell")

    def test_sla_and_priority(self):
        sev = calculate_severity("Issue", "Exposed electrical wire is sparking in the rain")
        self.assertEqual(sev, "High")
        priority = calculate_priority("Issue", sev, text="Exposed electrical wire is sparking in the rain")
        self.assertEqual(priority, "High")

        deadline = calculate_sla_deadline("High")
        self.assertIn("Z", deadline)
        status_info = evaluate_sla_status(deadline, "New")
        self.assertIn(status_info["status"], ["On Track", "Due Soon"])


class TestDatabaseOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_submission_lifecycle(self):
        sub_id, code = add_submission(
            submission_type="Issue",
            student_name="Test Student",
            anonymous=False,
            category="Infrastructure",
            location="Test Block",
            frequency="Daily",
            desired_outcome="Quick repair",
            description="Test issue regarding faulty classroom bench and broken desk.",
            image_filename=None,
            sentiment="Negative",
            severity="Medium",
            priority="Medium",
            priority_reason="Unit test record"
        )
        self.assertTrue(sub_id > 0)
        self.assertTrue(code.startswith("CV-"))

        # Upvote test
        count = increment_upvote(code)
        self.assertTrue(count >= 1)

        # Department routing test
        update_department(sub_id, "Estate & Facilities")
        item = get_submission_by_code(code)
        self.assertEqual(item["department"], "Estate & Facilities")

        # Status update test
        update_status(sub_id, "Resolved", "Bench was replaced by carpentry team.")
        item = get_submission_by_code(code)
        self.assertEqual(item["status"], "Resolved")
        self.assertEqual(item["resolution_note"], "Bench was replaced by carpentry team.")

    def test_executive_summary(self):
        summary = get_executive_summary()
        self.assertIn("total_submissions", summary)
        self.assertIn("departments", summary)
        self.assertIn("sla_compliance_rate", summary)


class TestWebEndpoints(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_public_pages(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

        r_board = self.client.get("/board")
        self.assertEqual(r_board.status_code, 200)

        r_track = self.client.get("/track")
        self.assertEqual(r_track.status_code, 200)

        r_health = self.client.get("/health")
        self.assertEqual(r_health.status_code, 200)
        data = json.loads(r_health.data)
        self.assertEqual(data["status"], "ok")

    def test_api_assist(self):
        payload = {
            "description": "The air conditioner in room 204 is making loud rattling noise and leaking water",
            "submission_type": "Issue"
        }
        res = self.client.post("/api/assist", json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["category"], "Infrastructure")
        self.assertIn("department", data)
        self.assertIn("quality", data)

    def test_admin_auth_guard(self):
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin", res.headers.get("Location", ""))

        res_rep = self.client.get("/admin/report")
        self.assertEqual(res_rep.status_code, 302)


if __name__ == "__main__":
    unittest.main()
