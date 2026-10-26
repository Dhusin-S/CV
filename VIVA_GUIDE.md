# Campus Voice — Project Presentation & Viva Guide

## 1. Project Overview & Elevator Pitch

> *"Campus Voice is an intelligent student grievance redressal and campus improvement platform. It bridges the trust gap between students and college administration by pairing transparent, reference-based tracking and community verification with automated NLP triage, department routing, and SLA compliance monitoring."*

---

## 2. System Architecture & Tech Stack

- **Backend Framework:** Python (Flask 3.x), WSGI-compliant, RESTful API endpoints.
- **Database Engine:** SQLite 3 with Write-Ahead Logging (WAL) mode enabled for concurrency and high-throughput read/writes without locking errors.
- **Machine Learning & NLP:**
  - `scikit-learn`: TF-IDF Vectorizer with n-gram range `(1, 2)` and cosine similarity for semantic duplicate identification and recurrence detection.
  - Transparent rule-based lexicon for sentiment and emotional tone classification (`Positive`, `Negative`, `Neutral`, `Frustrated`, `Concerned`, `Constructive`, `Appreciative`).
- **Frontend:** Vanilla modern HTML5, CSS3 Custom Properties (Design System), and asynchronous ES6 JavaScript (Fetch API, Canvas QR generation). Zero heavy frontend dependencies.
- **Security:** CSRF token verification on all POST/PUT mutations, HTTP-only Lax cookies, strict CSP and HTTP security headers, file-signature binary validation for image uploads.

---

## 3. Mathematical & Algorithmic Foundations

### A. TF-IDF & Cosine Similarity for Duplicate Detection
Each report description is vectorized using Term Frequency-Inverse Document Frequency:
$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \log\left(\frac{1 + |D|}{1 + |\{d \in D : t \in d\}|}\right) + 1$$

The semantic similarity between a new draft $A$ and existing campus issue $B$ is given by the cosine of the angle between their vector representations:
$$\text{Similarity}(A, B) = \frac{\vec{A} \cdot \vec{B}}{\|\vec{A}\| \|\vec{B}\|} = \frac{\sum_{i=1}^n A_i B_i}{\sqrt{\sum_{i=1}^n A_i^2} \sqrt{\sum_{i=1}^n B_i^2}}$$
*Threshold:* Reports with $\text{Similarity} \ge 0.42$ in the same category are grouped as recurring signals.

### B. Attention Score Formula (0 to 100)
Used in the Priority Queue to dynamically rank which open issue demands immediate administrative intervention:
$$\text{Score} = \text{Base}(\text{Priority}) + \min(20, \text{Similar} \times 5) + \min(20, \text{AgeDays} \times 2) + \min(15, \text{Upvotes} \times 3) + \text{FreqPoints}$$

Where:
- $\text{Base}(\text{Priority}) = 55$ for High, $35$ for Medium, $15$ for Low.
- $\text{FreqPoints} = 10$ (Ongoing), $8$ (Daily), $6$ (Several times a week), $4$ (Weekly).

### C. SLA (Service Level Agreement) Deadlines
- **High Priority:** 24 Hours ($T_{\text{created}} + 24\text{h}$)
- **Medium Priority:** 72 Hours ($T_{\text{created}} + 72\text{h}$)
- **Low Priority:** 168 Hours ($T_{\text{created}} + 7\text{d}$)

---

## 4. Key Questions & Model Answers for Viva / Examiners

### Q1: Why use a rule-based lexicon + TF-IDF instead of fine-tuning a deep transformer model like BERT or RoBERTa?
**Answer:**
1. **Explainability & Transparency:** In a university audit or grievance review, administrators need to know exactly why an issue was flagged as High Priority (e.g. electrical hazards or sanitary failures). Rule-based lexicons are 100% deterministic, auditable, and cannot hallucinate.
2. **Resource Efficiency & Speed:** TF-IDF runs in milliseconds on standard CPU hardware without GPU requirements, making it lightweight to deploy on standard campus servers or raspberry pi controllers.
3. **Resilience:** The system includes a fallback Jaccard token-overlap mechanism, ensuring the platform runs reliably even in resource-constrained environments.

### Q2: How does the system protect student privacy while preventing spam?
**Answer:**
1. **No Mandatory Accounts:** Students receive a cryptographically random reference code (`CV-XXXXXXXX`) with entropy $> 10^{14}$ possibilities.
2. **Anonymous Toggle:** When checked, student names are never saved to disk or database.
3. **Spam & Flooding Protection:** Rate-limiting on failed logins, session-guarded upvoting to prevent vote manipulation, client-side draft saving in `localStorage`, and server-side magic-byte validation on image uploads.

### Q3: How does this project meet accreditation standards (e.g., NAAC / NBA)?
**Answer:**
Accreditation criterion (such as NAAC Criterion 5.1.5) mandates a documented, time-bound grievance redressal mechanism with metrics on resolution efficiency. Campus Voice features a dedicated **Executive Accreditation Report (`/admin/report`)** providing department-wise breakdown, SLA compliance percentages, average resolution hours, and student sentiment indices.
