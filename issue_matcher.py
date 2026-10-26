import re

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


NORMALISATIONS = {
    "restroom": "restroom",
    "washroom": "restroom",
    "toilet": "restroom",
    "washrooms": "restroom",
    "toilets": "restroom",
    "wifi": "internet",
    "wi-fi": "internet",
    "network": "internet",
    "problems": "problem",
    "issues": "problem",
    "issue": "problem",
    "working": "work",
    "functioning": "work",
    "works": "work",
    "delayed": "late",
    "delays": "late",
    "buses": "bus",
    "varieties": "variety",
    "varities": "variety",
    "options": "option",
    "introduce": "add",
    "introducing": "add",
    "bring": "add",
    "bringing": "add",
    "adding": "add",
    "prices": "price",
    "cost": "price",
    "costs": "price",
    "cleaning": "clean",
    "cleanliness": "clean",
    "foods": "food",
    "meals": "food",
    "canteen": "canteen",
    "mess": "canteen",
    "cafeteria": "canteen"
}


def _normalise_text(value):
    text = re.sub(r"\s+", " ", (value or "").lower().strip())
    for old, new in NORMALISATIONS.items():
        text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)
    return text


def _jaccard_similarity(text1, text2):
    """Fallback token-overlap similarity when scikit-learn is unavailable."""
    set1 = set(re.findall(r"[a-z0-9]+", text1))
    set2 = set(re.findall(r"[a-z0-9]+", text2))
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def find_similar_submissions(target, submissions, threshold=0.30):
    candidates = []
    target_type = target.get("submission_type")
    target_category = _normalise_text(target.get("category"))

    for item in submissions:
        if item.get("id") == target.get("id"):
            continue
        if item.get("submission_type") != target_type:
            continue
        if _normalise_text(item.get("category")) != target_category:
            continue
        candidates.append(item)

    if not candidates:
        return []

    target_text = _normalise_text(target.get("description"))
    candidate_texts = [_normalise_text(item.get("description")) for item in candidates]

    if SKLEARN_AVAILABLE:
        try:
            texts = [target_text] + candidate_texts
            matrix = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2)
            ).fit_transform(texts)
            similarities = cosine_similarity(matrix[0:1], matrix[1:])[0]
        except Exception:
            similarities = [_jaccard_similarity(target_text, txt) for txt in candidate_texts]
    else:
        similarities = [_jaccard_similarity(target_text, txt) for txt in candidate_texts]

    results = []
    for item, score in zip(candidates, similarities):
        score = float(score)
        if score >= threshold:
            result = dict(item)
            result["similarity"] = round(score, 2)
            results.append(result)

    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results


def find_similar_issues(target, issues, threshold=0.30):
    return find_similar_submissions(target, issues, threshold)


def find_recent_similar(description, category, submission_type, existing_submissions, threshold=0.35, max_matches=3):
    """Fast similarity scanner for the real-time AI assistant."""
    if not description or len(description.strip()) < 10:
        return []

    target = {
        "id": -999,
        "submission_type": submission_type,
        "category": category,
        "description": description
    }
    matches = find_similar_submissions(target, existing_submissions, threshold=threshold)
    return matches[:max_matches]
