import re
from datetime import datetime, timedelta, timezone

HIGH_SEVERITY_PHRASES = {
    "danger", "dangerous", "unsafe", "fire", "electric shock",
    "exposed wire", "exposed electrical wire", "sparking", "sparks",
    "emergency", "accident", "injury", "short circuit",
    "serious hazard", "major hazard", "hazard", "hazardous",
    "completely broken", "not working at all", "unusable",
    "worms in the food", "worm in the food", "food has worms",
    "contaminated food", "food contamination",
    "ceiling falling", "gas leak"
}

MEDIUM_SEVERITY_PHRASES = {
    "broken", "dirty", "not clean", "very dirty", "damaged",
    "leaking", "not working", "does not work", "doesn't work",
    "unavailable", "overcrowded", "poor condition", "bad condition",
    "problem", "issue", "slow", "late", "delayed", "poor quality",
    "low quantity", "prices are high", "price is high",
    "too expensive", "not enough"
}

BROAD_SCOPE_PHRASES = {
    "whole college", "entire college", "across campus",
    "whole campus", "all blocks", "every block",
    "all classrooms", "entire block", "all students",
    "everyone", "college wide", "campus wide"
}

SLA_HOURS_MAP = {
    "High": 24,      # 1 day SLA
    "Medium": 72,    # 3 days SLA
    "Low": 168,      # 7 days SLA
    "None": 240      # 10 days review window
}


def _normalise(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def _contains(text, phrases):
    return any(phrase in text for phrase in phrases)


def calculate_severity(submission_type, text):
    if submission_type != "Issue":
        return "None"

    text = _normalise(text)

    if _contains(text, HIGH_SEVERITY_PHRASES):
        return "High"

    if _contains(text, MEDIUM_SEVERITY_PHRASES):
        return "Medium"

    return "Low"


def calculate_scope(text):
    text = _normalise(text)

    if _contains(text, BROAD_SCOPE_PHRASES):
        return 3

    if any(
        re.search(
            r"\b" + re.escape(word) + r"\b",
            text
        )
        for word in ["block", "classroom", "room", "lab", "floor", "washroom", "restroom"]
    ):
        return 2

    return 1


def calculate_recurrence_points(report_count, upvote_count=0):
    effective_count = report_count + (upvote_count // 2)
    if effective_count >= 5:
        return 3
    if effective_count >= 3:
        return 2
    if effective_count >= 1:
        return 1
    return 0


def calculate_priority(
    submission_type,
    severity,
    report_count=0,
    text="",
    upvote_count=0
):
    if submission_type != "Issue":
        return "None"

    text = _normalise(text)

    # Safety / health hazards are always urgent.
    if _contains(text, HIGH_SEVERITY_PHRASES):
        return "High"

    recurrence = calculate_recurrence_points(report_count, upvote_count)
    scope = calculate_scope(text)

    # Medium-severity problems are normally Medium.
    # Repeated, highly upvoted or broad problems become High.
    if severity == "Medium":
        if recurrence >= 2 or scope == 3 or upvote_count >= 5:
            return "High"
        return "Medium"

    # Low-severity problems become Medium if widespread/repeated.
    if recurrence >= 3 or scope == 3 or upvote_count >= 8:
        return "Medium"

    return "Low"


def calculate_sla_deadline(priority, start_time=None):
    """Calculates ISO timestamp for the SLA deadline based on priority."""
    if start_time is None:
        start_time = datetime.now(timezone.utc)
    elif isinstance(start_time, str):
        try:
            start_time = datetime.fromisoformat(start_time.replace("Z", "").replace("+00:00", "")).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            start_time = datetime.now(timezone.utc)

    hours = SLA_HOURS_MAP.get(priority, 72)
    deadline = start_time + timedelta(hours=hours)
    return deadline.strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate_sla_status(sla_deadline_str, current_status, resolved_at_str=None):
    """Computes SLA compliance label, remaining hours, and badge styling."""
    if not sla_deadline_str:
        return {"status": "On Track", "class": "sla-ok", "label": "Standard SLA", "hours_left": 48}

    try:
        deadline = datetime.fromisoformat(str(sla_deadline_str).replace("Z", "").replace("+00:00", "")).replace(tzinfo=timezone.utc)
    except Exception:
        return {"status": "On Track", "class": "sla-ok", "label": "On Track", "hours_left": 48}

    now = datetime.now(timezone.utc)

    if current_status in {"Resolved", "Implemented", "Acknowledged"}:
        resolved_time = now
        if resolved_at_str:
            try:
                resolved_time = datetime.fromisoformat(str(resolved_at_str).replace("Z", "").replace("+00:00", "")).replace(tzinfo=timezone.utc)
            except Exception:
                pass
        if resolved_time <= deadline:
            return {"status": "Met SLA", "class": "sla-met", "label": "Resolved on time", "hours_left": 0}
        else:
            diff_hours = round((resolved_time - deadline).total_seconds() / 3600, 1)
            return {"status": "Breached SLA", "class": "sla-overdue", "label": f"Resolved +{diff_hours}h overdue", "hours_left": 0}

    remaining_hours = (deadline - now).total_seconds() / 3600
    if remaining_hours < 0:
        overdue_h = round(abs(remaining_hours), 1)
        return {
            "status": "Overdue",
            "class": "sla-overdue",
            "label": f"Overdue by {overdue_h}h",
            "hours_left": round(remaining_hours, 1)
        }
    elif remaining_hours <= 12:
        return {
            "status": "Due Soon",
            "class": "sla-warning",
            "label": f"Due in {round(remaining_hours, 1)}h",
            "hours_left": round(remaining_hours, 1)
        }
    else:
        return {
            "status": "On Track",
            "class": "sla-ok",
            "label": f"{round(remaining_hours / 24, 1)}d remaining",
            "hours_left": round(remaining_hours, 1)
        }
