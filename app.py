import csv
import io
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, abort, jsonify, redirect, render_template, request,
    send_from_directory, session, url_for
)
from werkzeug.utils import secure_filename

from analyzer import (
    analyze_emotion, analyze_feedback, evaluate_content_quality,
    extract_keyphrases
)
from category import (
    ALL_DEPARTMENTS, analyze_category, analyze_category_with_confidence,
    department_for_category
)
from database import (
    add_submission, get_categories, get_departments, get_executive_summary,
    get_public_board, get_status_history, get_submission,
    get_submission_by_code, get_submissions, increment_upvote,
    initialize_database, update_admin_notes, update_analysis,
    update_department, update_status
)
from issue_matcher import (
    find_recent_similar, find_similar_issues, find_similar_submissions
)
from priority import (
    calculate_priority, calculate_scope, calculate_severity,
    calculate_sla_deadline, evaluate_sla_status
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "change-me-before-deployment"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_DESCRIPTION = 1600
MAX_NAME = 100
MAX_OUTCOME = 300
MAX_NOTES = 2000
MAX_STATUS_NOTE = 500
app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=4),
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_CATEGORIES = [
    "Infrastructure", "Internet & Technology", "Canteen", "Library", "Transport",
    "Academics", "Administration", "Cleanliness", "Safety", "Other", "General"
]
CAMPUS_AREAS = [
    "Academic Block", "Computer Lab", "Library", "Canteen", "Hostel",
    "Sports Area", "Main Gate", "Parking", "Transport / Bus", "Washrooms",
    "Administrative Office", "Campus-wide", "Other"
]
ISSUE_STATUSES = ["New", "Reviewing", "In Progress", "Resolved"]
SUGGESTION_STATUSES = ["New", "Under Review", "Planned", "Implemented", "Declined"]
APPRECIATION_STATUSES = ["New", "Acknowledged"]
SUBMISSION_TYPES = {"Issue", "Suggestion", "Appreciation"}
FREQUENCIES = ["Once", "Occasionally", "Weekly", "Several times a week", "Daily", "Ongoing"]

_login_attempts = {}
initialize_database()


def security_headers(response):
    if request.path.startswith(("/dashboard", "/issues", "/insights", "/submission", "/admin/report", "/api/")):
        response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; font-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
    return response


@app.after_request
def add_security_headers(response):
    return security_headers(response)


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def csrf_valid():
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    expected = session.get("csrf_token")
    return bool(supplied and expected and secrets.compare_digest(str(supplied), str(expected)))


def csrf_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not csrf_valid():
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Your session token is missing or expired. Refresh the page and try again."}), 400
            abort(400)
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def valid_image_signature(file_storage, extension):
    try:
        position = file_storage.stream.tell()
        header = file_storage.stream.read(16)
        file_storage.stream.seek(position)
    except Exception:
        return False
    if extension in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == "webp":
        return header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


def admin_required():
    return session.get("admin_logged_in") is True


def status_options(submission_type):
    if submission_type == "Issue":
        return ISSUE_STATUSES
    if submission_type == "Suggestion":
        return SUGGESTION_STATUSES
    return APPRECIATION_STATUSES


def recurrence_count(target, all_issues):
    return len(find_similar_issues(target, all_issues, threshold=0.42))


def priority_reason(severity, recurrence, scope, text, upvotes=0):
    if severity == "High":
        return "High-severity safety, health or critical-failure language detected."
    if recurrence >= 3:
        return f"Repeated signal: {recurrence} similar report(s) found across campus."
    if upvotes >= 5:
        return f"Community confirmed: {upvotes} students reported facing this issue."
    if scope == 3:
        return "Broad campus-wide scope detected."
    if severity == "Medium":
        return "Medium-severity operational problem requiring review."
    if recurrence >= 1:
        return f"Similar report detected ({recurrence} related)."
    return "Standard operational review queue."


def _safe_text(value, limit):
    return " ".join(str(value or "").split())[:limit]


def _client_key():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


def _login_allowed():
    now = time.time()
    key = _client_key()
    attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < 600]
    _login_attempts[key] = attempts
    return len(attempts) < 8


def _record_login_failure():
    key = _client_key()
    _login_attempts.setdefault(key, []).append(time.time())


def _clear_login_failures():
    _login_attempts.pop(_client_key(), None)


@app.context_processor
def inject_helpers():
    return {
        "status_options": status_options,
        "campus_areas": CAMPUS_AREAS,
        "max_description": MAX_DESCRIPTION,
        "csrf_token": csrf_token(),
        "frequencies": FREQUENCIES,
        "all_departments": ALL_DEPARTMENTS,
    }


@app.route("/")
def home():
    return render_template("index.html", categories=DEFAULT_CATEGORIES)


@app.route("/board")
def public_board():
    """Public Campus Resolution Board showcasing resolved fixes and active campus improvements."""
    records = get_public_board(limit=50)
    for r in records:
        r["sla_info"] = evaluate_sla_status(None, r["status"], r.get("updated_at"))
    return render_template("board.html", items=records, categories=DEFAULT_CATEGORIES)


@app.route("/api/board")
def public_board_api():
    """API for the public resolution feed."""
    records = get_public_board(limit=50)
    return jsonify({"items": records, "count": len(records)})


@app.route("/api/assist", methods=["POST"])
def live_assist():
    """Real-time AI writing assistant and duplicate detector for student submission portal."""
    data = request.get_json(silent=True) or {}
    description = str(data.get("description", "")).strip()
    submission_type = str(data.get("submission_type", "Issue")).strip()

    if not description:
        return jsonify({
            "category": "General", "confidence": 0, "sentiment": "Neutral",
            "emotion": "Neutral", "quality": evaluate_content_quality(""),
            "keyphrases": [], "similar_matches": [], "department": "Student Affairs & Welfare"
        })

    cat_analysis = analyze_category_with_confidence(description)
    predicted_category = cat_analysis["category"]
    confidence = cat_analysis["confidence"]
    department = cat_analysis["department"]

    sentiment = analyze_feedback(description)
    emotion = analyze_emotion(description, submission_type)
    quality = evaluate_content_quality(description)
    keyphrases = extract_keyphrases(description, max_phrases=3)

    # Fast duplicate check against unresolved issues
    similar_matches = []
    if len(description) >= 12 and submission_type in {"Issue", "Suggestion"}:
        all_submissions = get_submissions(submission_type=submission_type)
        open_items = [x for x in all_submissions if x.get("status") != "Resolved"]
        raw_similar = find_recent_similar(description, predicted_category, submission_type, open_items, threshold=0.35, max_matches=3)
        for s in raw_similar:
            similar_matches.append({
                "public_code": s.get("public_code"),
                "category": s.get("category"),
                "location": s.get("location"),
                "snippet": (s.get("description") or "")[:90] + "...",
                "similarity": s.get("similarity"),
                "upvotes": s.get("upvotes", 0)
            })

    return jsonify({
        "category": predicted_category,
        "confidence": confidence,
        "department": department,
        "sentiment": sentiment,
        "emotion": emotion,
        "quality": quality,
        "keyphrases": keyphrases,
        "similar_matches": similar_matches
    })


@app.route("/api/upvote/<public_code>", methods=["POST"])
def upvote_submission(public_code):
    """Students confirm an issue or support a suggestion ('Me Too' +1)."""
    item = get_submission_by_code(public_code)
    if not item:
        return jsonify({"error": "Submission not found"}), 404

    # Prevent spamming from the same session
    upvoted_key = f"upvoted_{item['id']}"
    if session.get(upvoted_key):
        return jsonify({"error": "You already confirmed this report", "upvotes": item.get("upvotes", 0)}), 429

    new_upvotes = increment_upvote(public_code)
    session[upvoted_key] = True

    # Recalculate priority if upvote surge warrants it
    if item["submission_type"] == "Issue" and item["priority"] != "High":
        new_priority = calculate_priority("Issue", item["severity"], 0, item["description"], upvote_count=new_upvotes)
        if new_priority != item["priority"]:
            reason = priority_reason(item["severity"], 0, calculate_scope(item["description"]), item["description"], upvotes=new_upvotes)
            update_analysis(item["id"], item["sentiment"], item["severity"], new_priority, reason)

    return jsonify({"success": True, "upvotes": new_upvotes, "public_code": public_code})


@app.route("/submit", methods=["POST"])
@csrf_required
def submit():
    submission_type = request.form.get("submission_type", "").strip()
    student_name = _safe_text(request.form.get("student_name", ""), MAX_NAME)
    anonymous = request.form.get("anonymous") == "on"
    category = request.form.get("category", "").strip() or "General"
    location = _safe_text(request.form.get("location", ""), 80)
    frequency = _safe_text(request.form.get("frequency", ""), 40)
    desired_outcome = _safe_text(request.form.get("desired_outcome", ""), MAX_OUTCOME)
    description = str(request.form.get("description", "")).strip()

    errors = []
    if submission_type not in SUBMISSION_TYPES:
        errors.append("Choose a feedback type.")
    if len(description) < 10:
        errors.append("Please provide at least 10 characters so the feedback can be understood.")
    if len(description) > MAX_DESCRIPTION:
        errors.append(f"Keep the message within {MAX_DESCRIPTION} characters.")
    if category not in DEFAULT_CATEGORIES:
        category = "General"
    if location and location not in CAMPUS_AREAS:
        location = "Other"
    if frequency and frequency not in FREQUENCIES:
        frequency = ""
    if anonymous:
        student_name = None
    if errors:
        return render_template("index.html", categories=DEFAULT_CATEGORIES, errors=errors, form=request.form), 400

    if category == "Other":
        category = analyze_category(description)

    sentiment = analyze_feedback(description)
    emotion = analyze_emotion(description, submission_type)
    tags = extract_keyphrases(description)
    department = department_for_category(category)

    severity = calculate_severity(submission_type, description)
    scope = calculate_scope(description)
    priority = "None"
    recurrence = 0
    if submission_type == "Issue":
        existing = get_submissions(submission_type="Issue")
        target = {"id": -1, "submission_type": "Issue", "category": category, "location": location, "description": description}
        recurrence = recurrence_count(target, existing)
        priority = calculate_priority("Issue", severity, recurrence, description)
    reason = priority_reason(severity, recurrence, scope, description)
    sla_deadline = calculate_sla_deadline(priority)

    image_filename = None
    image = request.files.get("image")
    if image and image.filename:
        if not allowed_file(image.filename):
            return render_template("index.html", categories=DEFAULT_CATEGORIES, errors=["Evidence must be PNG, JPG, JPEG or WEBP."], form=request.form), 400
        original = secure_filename(image.filename)
        if not original or "." not in original:
            return render_template("index.html", categories=DEFAULT_CATEGORIES, errors=["That evidence filename is not valid."], form=request.form), 400
        extension = original.rsplit(".", 1)[1].lower()
        if not valid_image_signature(image, extension):
            return render_template("index.html", categories=DEFAULT_CATEGORIES, errors=["The evidence file does not match its image format."], form=request.form), 400
        image_filename = f"{uuid.uuid4().hex}.{extension}"
        image.save(os.path.join(UPLOAD_FOLDER, image_filename))

    submission_id, public_code = add_submission(
        submission_type=submission_type, student_name=student_name, anonymous=anonymous,
        category=category, location=location, frequency=frequency, desired_outcome=desired_outcome,
        description=description, image_filename=image_filename, sentiment=sentiment,
        severity=severity, priority=priority, priority_reason=reason, department=department,
        emotion=emotion, tags=tags, sla_deadline=sla_deadline
    )
    item = get_submission(submission_id)
    return render_template("result.html", item=item)


@app.route("/track", methods=["GET", "POST"])
def track():
    code = request.values.get("code", "").strip().upper()
    if code:
        item = get_submission_by_code(code)
        if item:
            return redirect(url_for("track_detail", public_code=item["public_code"]))
        return render_template("track.html", code=code, error="We couldn't find that reference code. Check the code and try again.")
    return render_template("track.html")


@app.route("/track/<public_code>")
def track_detail(public_code):
    item = get_submission_by_code(public_code)
    if not item:
        abort(404)
    history = get_status_history(item["id"])
    sla_info = evaluate_sla_status(item.get("sla_deadline"), item["status"], item.get("updated_at"))
    parsed_tags = []
    if item.get("tags"):
        try:
            parsed_tags = json.loads(item["tags"])
        except Exception:
            parsed_tags = [t.strip() for t in item["tags"].split(",") if t.strip()]
    return render_template("track_detail.html", item=item, history=history, sla_info=sla_info, tags=parsed_tags)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if admin_required():
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        if not csrf_valid():
            return render_template("login.html", error="Your session expired. Refresh and try again."), 400
        if not _login_allowed():
            error = "Too many failed attempts. Please wait a few minutes and try again."
        elif secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            _clear_login_failures()
            session.clear()
            session["admin_logged_in"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            session.permanent = True
            return redirect(url_for("dashboard"))
        else:
            _record_login_failure()
            error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/dashboard")
def dashboard():
    if not admin_required():
        return redirect(url_for("admin_login"))
    categories = sorted(set(DEFAULT_CATEGORIES + get_categories()))
    departments = sorted(set(ALL_DEPARTMENTS + get_departments()))
    return render_template("dashboard.html", categories=categories, departments=departments)


@app.route("/insights")
def insights():
    if not admin_required():
        return redirect(url_for("admin_login"))
    return render_template("insights.html")


@app.route("/admin/report")
def admin_report():
    """Accreditation and Executive Management Health Report for College Leadership."""
    if not admin_required():
        return redirect(url_for("admin_login"))
    exec_summary = get_executive_summary()
    all_submissions = get_submissions()
    _enrich(all_submissions, all_submissions)
    analytics = _analytics(all_submissions, all_submissions)
    now_str = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
    return render_template("report.html", summary=exec_summary, analytics=analytics, generated_at=now_str)


def filtered_args():
    submission_type = request.args.get("type", "All")
    status = request.args.get("status", "All")
    priority = request.args.get("priority", "All")
    category = request.args.get("category", "All")
    department = request.args.get("department", "All")
    if submission_type not in SUBMISSION_TYPES and submission_type != "All":
        submission_type = "All"
    if category != "All" and category not in set(DEFAULT_CATEGORIES + get_categories()):
        category = "All"
    if department != "All" and department not in set(ALL_DEPARTMENTS + get_departments()):
        department = "All"
    if submission_type in SUBMISSION_TYPES and status not in status_options(submission_type):
        status = "All"
    if submission_type != "Issue":
        priority = "All"
    if priority not in {"All", "High", "Medium", "Low"}:
        priority = "All"
    if status == "All" or status in ISSUE_STATUSES + SUGGESTION_STATUSES + APPRECIATION_STATUSES:
        pass
    else:
        status = "All"
    date_range = request.args.get("date_range", "All")
    if date_range not in {"All", "7d", "30d", "90d"}:
        date_range = "All"
    return {
        "submission_type": submission_type,
        "category": category,
        "priority": priority,
        "status": status,
        "department": department,
        "search": _safe_text(request.args.get("search", ""), 120),
        "date_range": date_range,
    }


def csv_export(submissions):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Reference", "ID", "Type", "Category", "Department", "Location", "Frequency",
        "Desired Outcome", "Description", "Sentiment", "Emotion", "Severity", "Priority",
        "Priority Reason", "Status", "Upvotes", "SLA Deadline", "Student", "Anonymous",
        "Created At", "Updated At", "Resolution Note", "Admin Notes"
    ])
    for item in submissions:
        writer.writerow([
            item["public_code"], item["id"], item["submission_type"], item["category"],
            item.get("department") or "", item["location"] or "", item["frequency"] or "",
            item["desired_outcome"] or "", item["description"], item["sentiment"],
            item.get("emotion") or "Neutral", item["severity"], item["priority"],
            item["priority_reason"] or "", item["status"], item.get("upvotes", 0),
            item.get("sla_deadline") or "",
            "Anonymous" if item["anonymous"] else (item["student_name"] or "Not provided"),
            "Yes" if item["anonymous"] else "No", item["created_at"], item["updated_at"] or "",
            item["resolution_note"] or "", item["admin_notes"] or ""
        ])
    return output.getvalue()


@app.route("/export.csv")
def export_csv():
    if not admin_required():
        abort(401)
    response = app.response_class(csv_export(get_submissions(**filtered_args())), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=campus-voice-export.csv"
    return response


def _parse_created(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "").replace("+00:00", ""))
    except (TypeError, ValueError):
        return None


def _enrich(submissions, all_submissions):
    issues = [x for x in all_submissions if x["submission_type"] == "Issue"]
    suggestions = [x for x in all_submissions if x["submission_type"] == "Suggestion"]
    now = datetime.utcnow()
    for item in submissions:
        try:
            if item.get("submission_type") == "Issue":
                related = find_similar_issues(item, issues, threshold=0.42)
            elif item.get("submission_type") == "Suggestion":
                related = find_similar_submissions(item, suggestions, threshold=0.42)
            else:
                related = []
        except Exception:
            app.logger.exception("Similarity analysis failed for submission %s", item.get("id"))
            related = []
        item["similar_count"] = len(related)
        created = _parse_created(item.get("created_at"))
        item["age_days"] = max(0, (now - created).total_seconds() / 86400) if created else 0

        # Incorporate urgency, recurrence, upvotes, age and frequency
        upvotes = int(item.get("upvotes") or 0)
        score = 0
        if item["submission_type"] == "Issue" and item["status"] != "Resolved":
            score += {"High": 55, "Medium": 35, "Low": 15}.get(item.get("priority"), 0)
            score += min(20, item["similar_count"] * 5)
            score += min(20, item["age_days"] * 2)
            score += min(15, upvotes * 3)
            score += {"Ongoing": 10, "Daily": 8, "Several times a week": 6, "Weekly": 4}.get(item.get("frequency"), 0)
        elif item["submission_type"] == "Suggestion" and item["status"] not in {"Implemented", "Declined"}:
            score += 12
            score += min(12, item["similar_count"] * 4)
            score += min(12, upvotes * 2)
        item["attention_score"] = min(100, round(score))
        if item["attention_score"] >= 75:
            item["signal_label"] = "Act now"
        elif item["attention_score"] >= 45:
            item["signal_label"] = "Review soon"
        elif item["attention_score"] >= 20:
            item["signal_label"] = "Monitor"
        else:
            item["signal_label"] = "Routine"

        # Compute SLA compliance status
        sla_info = evaluate_sla_status(item.get("sla_deadline"), item.get("status"), item.get("updated_at"))
        item["sla_status"] = sla_info["status"]
        item["sla_label"] = sla_info["label"]
        item["sla_class"] = sla_info["class"]

    return submissions


def _trend_delta(all_submissions):
    now = datetime.utcnow()
    recent_start = now - timedelta(days=7)
    prior_start = now - timedelta(days=14)
    recent = sum(1 for x in all_submissions if (d := _parse_created(x.get("created_at"))) and d >= recent_start)
    prior = sum(1 for x in all_submissions if (d := _parse_created(x.get("created_at"))) and prior_start <= d < recent_start)
    if prior == 0:
        return {"recent": recent, "prior": prior, "delta_percent": 100 if recent else 0, "direction": "up" if recent else "flat"}
    delta = round((recent - prior) / prior * 100)
    return {"recent": recent, "prior": prior, "delta_percent": delta, "direction": "up" if delta > 0 else "down" if delta < 0 else "flat"}


def _emerging_signal(all_submissions):
    now = datetime.utcnow()
    recent_start = now - timedelta(days=7)
    prior_start = now - timedelta(days=14)
    recent, prior = {}, {}
    for x in all_submissions:
        created = _parse_created(x.get("created_at"))
        if not created:
            continue
        key = x.get("category") or "General"
        if created >= recent_start:
            recent[key] = recent.get(key, 0) + 1
        elif created >= prior_start:
            prior[key] = prior.get(key, 0) + 1
    candidates = []
    for key, count in recent.items():
        old = prior.get(key, 0)
        growth = ((count - old) / old * 100) if old else (100 if count else 0)
        candidates.append((growth, count, key, old))
    candidates = [c for c in candidates if c[1] >= 2]
    if not candidates:
        return {"name": "No clear emerging signal", "recent": 0, "prior": 0, "growth": 0}
    growth, count, key, old = max(candidates, key=lambda x: (x[0], x[1]))
    return {"name": key, "recent": count, "prior": old, "growth": round(growth)}


def _analytics(submissions, all_submissions):
    issues = [x for x in submissions if x["submission_type"] == "Issue"]
    suggestions = [x for x in submissions if x["submission_type"] == "Suggestion"]
    appreciations = [x for x in submissions if x["submission_type"] == "Appreciation"]
    open_issues = [x for x in issues if x["status"] != "Resolved"]
    high = [x for x in issues if x["priority"] == "High" and x["status"] != "Resolved"]
    resolved = [x for x in issues if x["status"] == "Resolved"]
    type_data = {"Issues": len(issues), "Suggestions": len(suggestions), "Appreciations": len(appreciations)}
    priority_data = {"High": 0, "Medium": 0, "Low": 0}
    category_data, location_data, status_data, frequency_data, department_data = {}, {}, {}, {}, {}
    sentiment_data = {"Negative": 0, "Neutral": 0, "Positive": 0}
    emotion_data = {"Frustrated": 0, "Concerned": 0, "Constructive": 0, "Appreciative": 0, "Neutral": 0}

    for x in submissions:
        category_data[x["category"]] = category_data.get(x["category"], 0) + 1
        dept = x.get("department") or department_for_category(x["category"])
        department_data[dept] = department_data.get(dept, 0) + 1
        if x.get("location"):
            location_data[x["location"]] = location_data.get(x["location"], 0) + 1
        status_data[x["status"]] = status_data.get(x["status"], 0) + 1
        sentiment = x.get("sentiment", "Neutral")
        sentiment_data[sentiment] = sentiment_data.get(sentiment, 0) + 1
        emotion = x.get("emotion") or "Neutral"
        emotion_data[emotion] = emotion_data.get(emotion, 0) + 1
        if x.get("frequency"):
            frequency_data[x["frequency"]] = frequency_data.get(x["frequency"], 0) + 1
        if x["submission_type"] == "Issue" and x["priority"] in priority_data:
            priority_data[x["priority"]] += 1

    trend = {}
    for x in submissions:
        day = str(x["created_at"])[:10]
        trend[day] = trend.get(day, 0) + 1
    trend = dict(sorted(trend.items())[-14:])

    age = {"< 1 day": 0, "1–3 days": 0, "4–7 days": 0, "8–30 days": 0, "30+ days": 0}
    for x in open_issues:
        days = x.get("age_days", 0)
        if days < 1:
            age["< 1 day"] += 1
        elif days < 3:
            age["1–3 days"] += 1
        elif days < 7:
            age["4–7 days"] += 1
        elif days < 30:
            age["8–30 days"] += 1
        else:
            age["30+ days"] += 1

    durations = []
    for x in resolved:
        history = get_status_history(x["id"])
        created = _parse_created(history[0]["created_at"]) if history else None
        resolved_at = next((_parse_created(e["created_at"]) for e in history if e["to_status"] == "Resolved"), None)
        if created and resolved_at:
            durations.append(max(0, (resolved_at - created).total_seconds() / 3600))
    avg_resolution_hours = round(sum(durations) / len(durations), 1) if durations else None

    # Overdue count
    overdue_count = sum(1 for x in open_issues if x.get("sla_status") == "Overdue")

    top_category = max(category_data.items(), key=lambda x: x[1], default=("—", 0))
    top_location = max(location_data.items(), key=lambda x: x[1], default=("—", 0))
    top_dept = max(department_data.items(), key=lambda x: x[1], default=("—", 0))
    negative_rate = round(sentiment_data.get("Negative", 0) / len(submissions) * 100) if submissions else 0
    attention_items = sorted(
        [dict(x) for x in submissions if x.get("submission_type") == "Issue" and x.get("status") != "Resolved"],
        key=lambda x: (-x.get("attention_score", 0), -x.get("age_days", 0))
    )
    trend_delta = _trend_delta(all_submissions)
    emerging = _emerging_signal(all_submissions)
    return {
        "total": len(submissions), "unfiltered_total": len(all_submissions), "issues": len(issues),
        "suggestions": len(suggestions), "appreciations": len(appreciations),
        "open_issues": len(open_issues), "high_priority": len(high), "resolved_issues": len(resolved),
        "resolution_rate": round(len(resolved) / len(issues) * 100) if issues else None,
        "avg_resolution_hours": avg_resolution_hours, "negative_rate": negative_rate,
        "overdue_count": overdue_count,
        "type_data": type_data, "priority_data": priority_data, "category_data": category_data,
        "location_data": location_data, "status_data": status_data, "sentiment_data": sentiment_data,
        "emotion_data": emotion_data, "department_data": department_data, "frequency_data": frequency_data,
        "trend": trend, "age_data": age,
        "top_category": {"name": top_category[0], "count": top_category[1]},
        "top_location": {"name": top_location[0], "count": top_location[1]},
        "top_department": {"name": top_dept[0], "count": top_dept[1]},
        "attention_items": attention_items[:6], "trend_delta": trend_delta, "emerging_signal": emerging,
    }


def _apply_filters_to_records(records, filters):
    result = []
    cutoff = None
    if filters.get("date_range") in {"7d", "30d", "90d"}:
        cutoff = datetime.utcnow() - timedelta(days=int(filters["date_range"][:-1]))
    for item in records:
        if filters.get("submission_type") != "All" and item.get("submission_type") != filters.get("submission_type"):
            continue
        if filters.get("category") != "All" and item.get("category") != filters.get("category"):
            continue
        if filters.get("priority") != "All" and item.get("priority") != filters.get("priority"):
            continue
        if filters.get("status") != "All" and item.get("status") != filters.get("status"):
            continue
        if filters.get("department") != "All" and item.get("department") != filters.get("department"):
            continue
        if cutoff:
            created = _parse_created(item.get("created_at"))
            if not created or created < cutoff:
                continue
        search = filters.get("search", "").lower().strip()
        if search:
            haystack = " ".join(str(item.get(k) or "") for k in ("description", "category", "location", "public_code", "desired_outcome", "department")).lower()
            if search not in haystack:
                continue
        result.append(item)
    return result


@app.route("/api/dashboard")
def dashboard_api():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        f = filtered_args()
        all_submissions = get_submissions()
        _enrich(all_submissions, all_submissions)
        submissions = _apply_filters_to_records(all_submissions, f)
        analytics = _analytics(submissions, all_submissions)
        analytics["submissions"] = submissions[:100]
        analytics["generated_at"] = datetime.utcnow().isoformat() + "Z"
        return jsonify(analytics)
    except Exception:
        app.logger.exception("Dashboard API failed")
        return jsonify({"error": "Dashboard data could not be loaded. Please retry."}), 500


@app.route("/api/insights")
def insights_api():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401
    all_submissions = get_submissions()
    _enrich(all_submissions, all_submissions)
    result = _analytics(all_submissions, all_submissions)
    result["generated_at"] = datetime.utcnow().isoformat() + "Z"
    return jsonify(result)


@app.route("/api/bulk-status", methods=["POST"])
@csrf_required
def bulk_status():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])
    status = str(data.get("status", "")).strip()
    if not isinstance(ids, list) or not ids or len(ids) > 100:
        return jsonify({"error": "Select between 1 and 100 submissions."}), 400
    updated = 0
    for raw_id in ids:
        try:
            item = get_submission(int(raw_id))
        except (TypeError, ValueError):
            item = None
        if not item or status not in status_options(item["submission_type"]):
            continue
        if update_status(item["id"], status, "Bulk workflow update"):
            updated += 1
    return jsonify({"updated": updated})


@app.route("/issues")
def issues():
    if not admin_required():
        return redirect(url_for("admin_login"))

    all_items = get_submissions()
    issue_list = [dict(x) for x in all_items if x.get("submission_type") == "Issue"]
    try:
        _enrich(issue_list, all_items)
    except Exception:
        app.logger.exception("Priority queue enrichment fallback triggered")
        now = datetime.utcnow()
        for item in issue_list:
            created = _parse_created(item.get("created_at"))
            age = max(0, (now - created).total_seconds() / 86400) if created else 0
            item["similar_count"] = 0
            item["age_days"] = age
            base = {"High": 55, "Medium": 35, "Low": 15}.get(item.get("priority"), 0)
            item["attention_score"] = min(100, round(base + min(20, age * 2))) if item.get("status") != "Resolved" else 0
            score = item["attention_score"]
            item["signal_label"] = "Act now" if score >= 75 else "Review soon" if score >= 45 else "Monitor" if score >= 20 else "Routine"
            item["sla_label"] = "Standard SLA"
            item["sla_class"] = "sla-ok"

    open_issues = [x for x in issue_list if x.get("status") != "Resolved"]
    open_issues.sort(key=lambda x: (-float(x.get("attention_score") or 0), -float(x.get("age_days") or 0), -int(x.get("id") or 0)))
    queue_stats = {
        "unresolved": len(open_issues),
        "high": sum(1 for x in open_issues if x.get("priority") == "High"),
        "repeated": sum(1 for x in open_issues if (x.get("similar_count") or 0) > 0 or (x.get("upvotes") or 0) > 0),
        "oldest_days": round(max((float(x.get("age_days") or 0) for x in open_issues), default=0)),
        "critical": sum(1 for x in open_issues if float(x.get("attention_score") or 0) >= 75),
        "overdue": sum(1 for x in open_issues if x.get("sla_status") == "Overdue"),
    }
    departments = sorted(set(ALL_DEPARTMENTS + get_departments()))
    return render_template("issues.html", issues=open_issues, queue_stats=queue_stats, departments=departments)


@app.route("/submission/<int:submission_id>")
def submission_detail(submission_id):
    if not admin_required():
        return redirect(url_for("admin_login"))
    item = get_submission(submission_id)
    if item is None:
        abort(404)
    all_items = get_submissions()
    _enrich([item], all_items)
    if item["submission_type"] == "Issue":
        similar = find_similar_issues(item, [x for x in all_items if x["submission_type"] == "Issue"], threshold=0.42)
    elif item["submission_type"] == "Suggestion":
        similar = find_similar_submissions(item, [x for x in all_items if x["submission_type"] == "Suggestion"], threshold=0.42)
    else:
        similar = []
    history = get_status_history(submission_id)
    parsed_tags = []
    if item.get("tags"):
        try:
            parsed_tags = json.loads(item["tags"])
        except Exception:
            parsed_tags = [t.strip() for t in item["tags"].split(",") if t.strip()]

    return render_template(
        "submission.html", item=item, similar=similar, history=history,
        status_options=status_options(item["submission_type"]),
        departments=ALL_DEPARTMENTS, tags=parsed_tags
    )


@app.route("/submission/<int:submission_id>/status", methods=["POST"])
@csrf_required
def change_status(submission_id):
    if not admin_required():
        return redirect(url_for("admin_login"))
    item = get_submission(submission_id)
    if not item:
        abort(404)
    status = request.form.get("status", "").strip()
    note = _safe_text(request.form.get("status_note", ""), MAX_STATUS_NOTE)
    if status in status_options(item["submission_type"]):
        update_status(submission_id, status, note)
    return redirect(url_for("submission_detail", submission_id=submission_id))


@app.route("/submission/<int:submission_id>/department", methods=["POST"])
@csrf_required
def change_department(submission_id):
    if not admin_required():
        return redirect(url_for("admin_login"))
    item = get_submission(submission_id)
    if not item:
        abort(404)
    department = request.form.get("department", "").strip()
    if department in ALL_DEPARTMENTS or department:
        update_department(submission_id, department)
    return redirect(url_for("submission_detail", submission_id=submission_id))


@app.route("/submission/<int:submission_id>/notes", methods=["POST"])
@csrf_required
def save_notes(submission_id):
    if not admin_required():
        return redirect(url_for("admin_login"))
    if not get_submission(submission_id):
        abort(404)
    update_admin_notes(submission_id, _safe_text(request.form.get("admin_notes", ""), MAX_NOTES))
    return redirect(url_for("submission_detail", submission_id=submission_id))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if not admin_required():
        abort(404)
    safe = secure_filename(filename)
    if safe != filename or not safe:
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, safe)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "campus-voice",
        "version": "v7.0-enterprise",
        "features": ["ai-assist", "public-board", "department-routing", "sla-tracking", "community-signals"]
    })


@app.errorhandler(400)
def bad_request(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Bad request"}), 400
    return render_template("404.html", admin=admin_required(), message="That request could not be processed."), 400


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    if request.path.startswith("/admin") or session.get("admin_logged_in"):
        return render_template("404.html", admin=True), 404
    return render_template("404.html", admin=False), 404


@app.errorhandler(500)
def server_error(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("500.html"), 500


@app.errorhandler(413)
def too_large(_error):
    if request.path.startswith("/submit"):
        return render_template("index.html", categories=DEFAULT_CATEGORIES, errors=["The upload is too large. Keep the evidence image under 5 MB."]), 413
    return "Request too large", 413


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
