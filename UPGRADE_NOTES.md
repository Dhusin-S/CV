# Campus Voice — Enterprise Upgrade Release Notes (v7.0)

## Overview of Major Enhancements

The **Campus Voice** platform has been upgraded from a basic feedback logger into an **enterprise-grade campus intelligence, grievance redressal, and SLA accountability system**.

---

### 1. ⚡ Real-Time AI Writing Assistant & Live Duplicate Prevention
- **Endpoint:** `POST /api/assist`
- **Interactive Triage on `index.html`:** As the student types their description, a debounced background worker analyzes the input in real time.
- **Auto Category Suggestion:** Infers the most appropriate category with confidence score (e.g. *Infrastructure 85%*) with a one-click **"Apply ↵"** button.
- **Emotion & Tone Detection:** Classifies student emotional state into *Frustrated*, *Concerned*, *Constructive*, *Appreciative*, or *Neutral*.
- **Quality Feedback Bar:** Evaluates report quality (0–100) and offers real-time guidance (e.g., prompting students to mention exact classrooms or affected equipment).
- **Live Duplicate Detection:** Compares the active draft against unresolved campus reports using TF-IDF and semantic similarity. Warns the student if a similar issue was recently filed and provides a direct link to track or confirm it.

---

### 2. 🏛️ Public Campus Resolution & Transparency Board
- **Route:** `GET /board` (accessible without admin credentials)
- **Purpose:** Solves the classic "black hole" complaint box problem by showcasing verified resolutions and active campus improvements.
- **Features:**
  - Displays what was resolved, which department resolved it, and the official action taken.
  - Interactive search and category/status filters.
  - Complete privacy: student names and internal admin notes are strictly excluded.
  - **Community Confirmations ("Me Too" +1):** Students experiencing the same issue can click "Me Too" to upvote the issue.

---

### 3. 🎯 Department Routing & Operational Units
Submissions are automatically routed to responsible campus departments based on domain classification:
1. **Estate & Facilities** (Infrastructure, electricity, classrooms, ACs)
2. **IT & Systems Cell** (Wi-Fi, computer labs, portals, ERP)
3. **Canteen & Food Committee** (Dining, cafeteria, food quality)
4. **Library Services** (Books, reading rooms, digital catalog)
5. **Transport Management** (Buses, parking, routes)
6. **Academic Section** (Faculty, exams, schedules, marks)
7. **Administrative Office** (Fees, certificates, ID cards)
8. **Sanitation & Housekeeping** (Restrooms, waste, cleanliness)
9. **Campus Security & Safety** (Guards, emergency hazards, lighting)
10. **Student Affairs & Welfare** (General student support)

Administrators can seamlessly reassign or transfer any ticket directly from `submission.html` with an automatic entry into the audit trail.

---

### 4. ⏱️ SLA (Service Level Agreement) Management & Overdue Alerts
- **High Priority Issues:** 24-Hour SLA Target
- **Medium Priority Issues:** 72-Hour SLA Target
- **Low Priority Issues:** 7-Day SLA Target
- **Visual SLA Badges:**
  - `On Track` (Green)
  - `Due Soon` (Amber, within 12 hours of deadline)
  - `Overdue` (Red, past resolution deadline)
  - `Resolved on Time` / `Resolved Overdue` (Historical tracking)
- Integrated into Overview Dashboard, Priority Queue, Detail View, and Student Tracking Pass.

---

### 5. 📊 Institutional Executive Accreditation Report
- **Route:** `GET /admin/report`
- **Purpose:** Formatted specifically for college leadership, Principal/Dean reviews, and accreditation bodies (e.g., **NAAC Criterion 5: Student Support and Progression**, **NBA**, **ABET**).
- **Included Metrics:**
  - Total feedback volume and resolution percentages.
  - Departmental grievance & turnaround matrix with urgency flags.
  - SLA Compliance Rate (% of complaints resolved within target window).
  - Sentiment & Emotional Tone distributions.
  - Emerging campus hotspots and week-over-week trends.
  - Ready for 1-click browser printing or PDF archiving (`window.print()`).

---

### 6. 📱 Digital Submission Pass with Offline QR Code
- Generated on submission confirmation (`result.html`) and lookup (`track_detail.html`).
- Generates a lightweight, zero-dependency offline SVG QR code directing directly to the student's private tracking link.
- Provides a clean "Print / Save Pass" interface for students to keep receipts without creating accounts.

---

### 7. 🧪 Comprehensive Automated Test Suite
- **File:** `test_app.py`
- Tests NLP classification, emotion extraction, SLA logic, database migrations, community upvoting, and route authorization.
- Runs natively with Python's standard `unittest`:
  ```bash
  python -m unittest test_app.py
  ```

---

### 8. 🌱 Realistic Demo Data Seeder
- **File:** `seed_data.py`
- Populates diverse, realistic campus submissions across all departments, categories, and SLA states for instant demonstration.
  ```bash
  python seed_data.py
  ```
