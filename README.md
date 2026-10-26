# Campus Voice — Enterprise Edition (v7.0)

Campus Voice is a modern, full-stack student feedback, grievance redressal, and campus operations platform built with Flask, SQLite, and scikit-learn.

---

## 🚀 Key Features & Highlights

### 🎓 Student Experience
- **Structured Feedback Composer:** Choose between *Issue*, *Suggestion*, or *Appreciation* with guided prompts.
- **⚡ Live AI Writing Assistant (`/api/assist`):** Real-time category inference with confidence %, emotional tone analysis, and content quality feedback.
- **⚠️ Live Duplicate Prevention:** Warns students if an unresolved report on the same issue already exists in the same area.
- **🏛️ Public Resolution Board (`/board`):** Transparent view of completed campus improvements ("Fixed & Improved") and ongoing maintenance.
- **▲ "Me Too" Community Confirmations:** Students can confirm/upvote an existing issue without filing duplicate complaints.
- **📱 Digital Submission Pass & Offline QR Code:** Auto-generated vector QR code for scanning or printing on mobile without logging into an account.
- **🔒 Privacy by Design:** 1-click anonymous mode completely omits student names from database storage while preserving tracking references.

### 🏢 Operations & Administration
- **Operational Console (`/dashboard`):** Real-time KPIs, incoming momentum charts, emerging category alerts, and live work queue.
- **Live Priority Queue (`/issues`):** Action-first queue prioritized by urgency, recurrence, community confirmations, and SLA turnaround.
- **🎯 10-Department Automatic Routing:** Automatically maps issues to campus departments (IT, Estate & Facilities, Canteen, Library, etc.) with manual re-routing tools.
- **⏱️ SLA Tracking & Overdue Warnings:** Strict resolution SLAs (High = 24h, Medium = 72h, Low = 7d) with dynamic countdown badges (`On Track`, `Due Soon`, `Overdue`).
- **📊 Executive Accreditation Report (`/admin/report`):** Formal institutional audit report formatted for College Principals, Deans, and NAAC/NBA accreditation reviews.
- **Insights & Pattern Detection (`/insights`):** Campus hotspots, aging distributions, sentiment trends, and category clustering.
- **Bulk Workflow Actions & CSV Export:** Process multiple tickets simultaneously and export filtered views.

---

## 🛠️ Tech Stack & Architecture

- **Backend:** Python 3.10+ / Flask 3.x
- **Data Persistence:** SQLite 3 (WAL mode, busy timeout, indexed schema migrations)
- **Machine Learning & NLP:**
  - `scikit-learn` TF-IDF Vector Space Model & Cosine Similarity
  - Lexicon-backed Sentiment & Emotional Tone Classifier
  - Rule-based keyword extraction and quality evaluator
- **Security:** CSRF tokens, strict Content Security Policy, secure HTTP-only cookies, magic-byte image validation.
- **Frontend:** Pure HTML5, modern CSS3 custom properties design system, vanilla ES6 JavaScript.

---

## 🏃 Quick Start

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. (Optional) Seed Demo Data
Populate the database with realistic campus feedback spanning diverse categories, departments, and SLA statuses:
```bash
python seed_data.py
```

### 3. Run the Automated Tests
```bash
python -m unittest test_app.py
```

### 4. Start the Application
```bash
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

- Default Administrator Password: `change-me-before-deployment` (or set via `ADMIN_PASSWORD` env variable).

---

## 🗺️ Application Routes

### Public Endpoints
- `/` — Student feedback submission portal with live AI assist
- `/board` — Public campus resolution & transparency board
- `/track` — Public reference code lookup
- `/track/<public_code>` — Private submission workflow timeline & digital pass
- `/api/assist` — Real-time AI category, tone & duplicate check API
- `/api/upvote/<public_code>` — Community "+1 Me Too" confirmation API
- `/health` — Service health & feature matrix response

### Administrator Endpoints
- `/admin` — Secure administrator sign-in
- `/dashboard` — Operational overview with department & SLA filters
- `/issues` — Priority queue sorted by attention score & urgency
- `/insights` — Deep campus analytics and hotspot distributions
- `/admin/report` — Printable Institutional Accreditation Health Report
- `/submission/<id>` — Detailed ticket triage, department routing & notes
- `/export.csv` — Filtered CSV data export

---

## 📚 Viva & Presentation Resources
- See **`UPGRADE_NOTES.md`** for a detailed changelog of all enterprise improvements.
- See **`VIVA_GUIDE.md`** for mathematical formulas, architecture diagrams, and examiner Q&A.
