import re

# Transparent, viva-friendly sentiment, emotion and keyphrase intelligence.
# Rule-based and lexicon-backed for explainability and deterministic behavior.

POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "helpful", "clean",
    "improved", "better", "nice", "love", "liked", "like",
    "appreciate", "appreciated", "useful", "friendly", "fast",
    "convenient", "comfortable", "effective", "perfect", "awesome",
    "satisfied", "smooth", "reliable", "safe", "well", "kudos",
    "thank", "thanks", "thankful", "efficient", "resolved", "neat"
}

NEGATIVE_WORDS = {
    "bad", "poor", "broken", "dirty", "slow", "worst", "unusable",
    "problem", "problems", "issue", "issues", "damaged", "leaking",
    "unsafe", "terrible", "uncomfortable", "failure", "failed",
    "delay", "delays", "delayed", "late", "missing", "overcrowded",
    "unavailable", "difficult", "difficulties", "disappointing",
    "disappointed", "hate", "horrible", "useless", "poorly",
    "worm", "worms", "contaminated", "contamination", "smell",
    "smelly", "garbage", "dust", "fault", "faulty", "crash",
    "crashes", "error", "errors", "expensive", "unfair", "suffocating",
    "choked", "stinking", "dark", "hazardous", "spark", "sparks"
}

NEGATIVE_PHRASES = {
    "not good", "not great", "not clean", "not working",
    "not functioning", "not available", "not usable",
    "not comfortable", "does not work", "doesn't work",
    "do not work", "don't work", "did not work", "didn't work",
    "isn't working", "is not working", "are not working",
    "are not clean", "very poor", "really poor", "very bad",
    "really bad", "poor quality", "bad quality", "not satisfied",
    "not happy", "cannot use", "can't use", "not maintained",
    "not enough", "prices are high", "price is high",
    "food is expensive", "too expensive", "very late",
    "food has worms", "worms in the food", "worm in the food"
}

POSITIVE_PHRASES = {
    "very good", "really good", "very clean", "really clean",
    "very helpful", "really helpful", "very useful", "really useful",
    "works well", "working well", "well maintained", "high quality",
    "very comfortable", "really comfortable", "very satisfied",
    "highly recommended", "very reliable", "very safe",
    "not only good but excellent", "not only good", "not bad",
    "great job", "keep it up", "much appreciated"
}

NEGATIONS = {
    "not", "never", "neither", "nor", "isn't", "wasn't", "weren't",
    "doesn't", "don't", "didn't", "can't", "cannot", "couldn't",
    "won't", "wouldn't"
}

EMOTION_KEYWORDS = {
    "Frustrated": {
        "terrible", "horrible", "worst", "unacceptable", "disaster", "fed up",
        "sick of", "useless", "ridiculous", "disappointed", "disappointing",
        "hate", "angry", "furious", "ruined", "screwed", "crashes"
    },
    "Concerned": {
        "unsafe", "danger", "dangerous", "hazard", "risk", "worried",
        "worrying", "scary", "fear", "electric shock", "sparking",
        "contaminated", "emergency", "accident", "injury", "broken", "leak"
    },
    "Constructive": {
        "suggest", "propose", "recommend", "idea", "improvement", "could",
        "should", "would be better", "how about", "request", "hope",
        "upgrade", "solution", "alternative", "introduce"
    },
    "Appreciative": {
        "thank", "thanks", "grateful", "appreciate", "appreciated", "kudos",
        "awesome", "excellent", "love", "helpful", "great job", "wonderful"
    }
}

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "can",
    "could", "should", "would", "i", "we", "you", "they", "it", "my", "our",
    "your", "this", "that", "these", "those", "there", "here", "very", "so",
    "too", "just", "please", "kindly", "also", "any", "some"
}


def _normalise(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def analyze_feedback(text):
    text = _normalise(text)
    if not text:
        return "Neutral"

    if any(phrase in text for phrase in NEGATIVE_PHRASES):
        return "Negative"

    if any(phrase in text for phrase in POSITIVE_PHRASES):
        return "Positive"

    words = re.findall(r"[a-zA-Z']+", text)
    positive_score = 0
    negative_score = 0

    for index, word in enumerate(words):
        previous = words[max(0, index - 3):index]
        negated = any(token in NEGATIONS for token in previous)

        if word in POSITIVE_WORDS:
            if negated:
                negative_score += 2
            else:
                positive_score += 1
        elif word in NEGATIVE_WORDS:
            if negated:
                positive_score += 2
            else:
                negative_score += 1

    if negative_score > positive_score:
        return "Negative"
    if positive_score > negative_score:
        return "Positive"
    return "Neutral"


def analyze_emotion(text, submission_type="Issue"):
    """Infer the student's emotional tone for empathetic and contextual triage."""
    text = _normalise(text)
    if not text:
        return "Neutral"

    scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                if kw in text:
                    scores[emotion] += 3
            else:
                if re.search(r"\b" + re.escape(kw) + r"\b", text):
                    scores[emotion] += 2

    # Prioritize according to submission context
    if submission_type == "Appreciation":
        scores["Appreciative"] += 2
    elif submission_type == "Suggestion":
        scores["Constructive"] += 2

    top_emotion = max(scores, key=scores.get)
    if scores[top_emotion] > 0:
        return top_emotion

    sentiment = analyze_feedback(text)
    if sentiment == "Negative":
        return "Frustrated" if submission_type == "Issue" else "Concerned"
    if sentiment == "Positive":
        return "Appreciative"
    return "Constructive" if submission_type == "Suggestion" else "Neutral"


def extract_keyphrases(text, max_phrases=3):
    """Extract prominent 2-3 word topic phrases without heavy dependencies."""
    text = _normalise(text)
    words = [w for w in re.findall(r"[a-z0-9\-]+", text) if len(w) > 2]
    if not words:
        return []

    # Count candidate bigrams & trigrams filtering stopwords
    candidates = {}
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            gram = words[i:i + n]
            if gram[0] in STOP_WORDS or gram[-1] in STOP_WORDS:
                continue
            if any(w in STOP_WORDS for w in gram) and n == 2:
                continue
            phrase = " ".join(gram)
            # Avoid generic words
            if len(phrase) >= 6:
                candidates[phrase] = candidates.get(phrase, 0) + 1

    # Add strong standalone informative words if few phrases
    if len(candidates) < max_phrases:
        for w in words:
            if w not in STOP_WORDS and len(w) > 4 and (w in POSITIVE_WORDS or w in NEGATIVE_WORDS or any(w in kws for kws in EMOTION_KEYWORDS.values())):
                candidates[w] = candidates.get(w, 0) + 1

    sorted_phrases = sorted(candidates.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
    results = []
    for phrase, _ in sorted_phrases:
        if not any(phrase in existing or existing in phrase for existing in results):
            results.append(phrase)
        if len(results) >= max_phrases:
            break
    return results


def evaluate_content_quality(text):
    """Provide real-time guidance score and feedback for students composing feedback."""
    text = (text or "").strip()
    length = len(text)
    if length < 10:
        return {
            "score": 10,
            "badge": "Too brief",
            "hint": "Please add more details about what happened so the campus team can act on it.",
            "is_ready": False
        }

    score = min(50, length // 6)
    hints = []

    has_location = bool(re.search(r"\b(room|block|floor|lab|hall|ground|gate|canteen|library|washroom|toilet|bus)\b", text, re.I))
    if has_location:
        score += 25
    else:
        hints.append("Mention specific locations (e.g., 'Block B 2nd floor')")

    has_effect = bool(re.search(r"\b(because|since|affecting|unable|cannot|hard|delay|smell|students|class)\b", text, re.I))
    if has_effect:
        score += 25
    else:
        hints.append("Explain how it affects students or campus activities")

    score = min(100, score)
    if score >= 80:
        badge = "Excellent report"
        hint = "Clear context and actionable details provided."
    elif score >= 50:
        badge = "Good details"
        hint = " + ".join(hints) if hints else "Good information. Clear and concise."
    else:
        badge = "Needs detail"
        hint = " + ".join(hints) if hints else "Add more specifics for faster resolution."

    return {
        "score": score,
        "badge": badge,
        "hint": hint,
        "is_ready": length >= 10
    }
