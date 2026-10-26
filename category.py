import re

CATEGORY_KEYWORDS = {
    "Infrastructure": [
        "fan", "light", "classroom", "desk", "chair", "building",
        "projector", "ac", "air conditioner", "lift", "room",
        "furniture", "electricity", "power", "bench", "blackboard",
        "whiteboard", "speaker", "audio", "podium", "door", "window"
    ],
    "Internet & Technology": [
        "wifi", "wi-fi", "internet", "network", "computer", "pc",
        "system", "portal", "website", "printer", "software", "login",
        "server", "ethernet", "lan", "erp", "app", "broadband"
    ],
    "Canteen": [
        "canteen", "food", "meal", "lunch", "breakfast", "snack",
        "water", "menu", "price", "food quality", "food quantity",
        "tea", "coffee", "hygiene", "plate", "taste", "dining"
    ],
    "Library": [
        "library", "book", "books", "reading", "study room",
        "librarian", "borrow", "journal", "reference", "digital library",
        "catalog", "ebook"
    ],
    "Transport": [
        "bus", "transport", "driver", "route", "vehicle", "parking",
        "college bus", "shuttle", "commute", "traffic", "timing"
    ],
    "Academics": [
        "class", "subject", "exam", "assignment", "teacher",
        "faculty", "lecture", "lab", "marks", "timetable",
        "course", "syllabus", "attendance", "grade", "practicals"
    ],
    "Administration": [
        "office", "certificate", "fees", "staff", "administration",
        "document", "approval", "id card", "scholarship", "bonafide",
        "clerk", "counter", "fee receipt"
    ],
    "Cleanliness": [
        "dirty", "clean", "garbage", "dust", "washroom", "toilet",
        "restroom", "smell", "waste", "sanitation", "dustbin", "litter",
        "clogged", "drainage", "stink", "stinking", "cleaning"
    ],
    "Safety": [
        "unsafe", "danger", "dangerous", "security", "accident",
        "fire", "hazard", "emergency", "exposed wire", "electric shock",
        "guard", "harassment", "bullying", "cctv", "lighting", "dark spot"
    ]
}

CATEGORY_TO_DEPARTMENT = {
    "Infrastructure": "Estate & Facilities",
    "Internet & Technology": "IT & Systems Cell",
    "Canteen": "Canteen & Food Committee",
    "Library": "Library Services",
    "Transport": "Transport Management",
    "Academics": "Academic Section",
    "Administration": "Administrative Office",
    "Cleanliness": "Sanitation & Housekeeping",
    "Safety": "Campus Security & Safety",
    "General": "Student Affairs & Welfare",
    "Other": "Student Affairs & Welfare"
}

ALL_DEPARTMENTS = [
    "Estate & Facilities",
    "IT & Systems Cell",
    "Canteen & Food Committee",
    "Library Services",
    "Transport Management",
    "Academic Section",
    "Administrative Office",
    "Sanitation & Housekeeping",
    "Campus Security & Safety",
    "Student Affairs & Welfare"
]


def department_for_category(category):
    return CATEGORY_TO_DEPARTMENT.get(category, "Student Affairs & Welfare")


def analyze_category(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if " " in keyword:
                if keyword in text:
                    score += 2
            else:
                if re.search(r"\b" + re.escape(keyword) + r"\b", text):
                    score += 1
        scores[category] = score

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"


def analyze_category_with_confidence(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if " " in keyword:
                if keyword in text:
                    score += 2
            else:
                if re.search(r"\b" + re.escape(keyword) + r"\b", text):
                    score += 1
        scores[category] = score

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round((scores[best] / total * 100)) if total > 0 else 0
    return {
        "category": best if scores[best] > 0 else "General",
        "confidence": confidence,
        "department": department_for_category(best if scores[best] > 0 else "General"),
        "scores": scores
    }
