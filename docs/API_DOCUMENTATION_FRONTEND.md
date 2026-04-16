# MentorMuni API — Simple Guide for Frontend

Add the MentorMuni API to your frontend in 3 steps. Copy the code and change the URL.

---

## Before You Start

1. Get your API URL (e.g. `https://your-app.railway.app`)
2. Always send `Content-Type: application/json` for POST requests
3. All requests return JSON

---

## API 1: Interview Ready (Profile → Questions → Results)

### Part A: Get Questions (when user clicks "Get My Readiness Plan")

**URL:** `POST your-api-url/interview-ready/plan`

**Send this:**
```json
{
  "user_type": "it_professional",
  "primary_skill": "React"
}
```

**`user_type` (same canonical set for legacy plan, interview-readiness plan, and skill-readiness plan):**  
Use one of: `college_student_year_1`, `college_student_year_2`, `college_student_year_3`, `college_student_year_4`, `it_professional`.  
Older UI strings still work and are normalized (e.g. `"student"` → `college_student_year_4`, `"Working Professional"` → `it_professional`, `"3rd year student"` → `college_student_year_3`).

You can also send `email` and `phone` if you have them. They are optional.

**You get back:** A list of 15 questions. Save the full list — you need it for the next step.

**Example response:**
```json
{
  "evaluation_plan": [
    {
      "question": "Can you explain dependency injection?",
      "correct_answer": "Yes",
      "study_topic": "Dependency Injection"
    }
  ]
}
```

**Code:**
```javascript
const API_URL = "https://your-api.railway.app";

async function getQuestions(profile) {
  const res = await fetch(`${API_URL}/interview-ready/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_type: profile.userType,      // e.g. college_student_year_4 or it_professional (legacy labels OK)
      primary_skill: profile.primarySkill,
      email: profile.email || null,
      phone: profile.phone || null
    })
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "Something went wrong");
    return;
  }
  const data = await res.json();
  return data.evaluation_plan;  // save this!
}
```

---

### Part B: Show Questions to User

**Legacy plan only** (`POST /interview-ready/plan`): every row is Yes/No. There is no `question_type` on items — only `question`, `correct_answer`, `study_topic`.

**Skill readiness** (`/interview-ready/skill-readiness/plan`) and **Interview readiness** (`/interview-ready/interview-readiness/plan`): each item has `question_type`:

| `question_type` | UI | Store one value per question |
|-----------------|-----|------------------------------|
| `yes_no` | Yes / No | `"Yes"` or `"No"` |
| `multiple_choice` | Four choices (from `options`) | `"A"`, `"B"`, `"C"`, or `"D"` |
| `scenario` | Four choices | `"A"`–`"D"` |
| `code_mcq` | Four choices (code is inside `question`) | `"A"`–`"D"` |

Expected order (15 questions): positions 1–4 `yes_no`, 5–11 `multiple_choice`, 12–13 `scenario`, 14–15 `code_mcq`. Each item includes `explanation` (optional to show after the user answers, or on a review screen).

Build `userAnswers` as a **parallel array of 15 strings** in plan order, e.g. `["Yes","No","Yes","Yes","B","A",...,"D","C"]`.

---

### Part C: Get Results (when user clicks "See My Results")

**URL:** `POST your-api-url/interview-ready/evaluate`

**Send this:** Use the saved plan + user answers. The API does not receive `question_type`; it only compares strings.

```json
{
  "questions": ["question 1", "question 2", ...],
  "answers": ["Yes", "No", "B", "A", ...],
  "correct_answers": ["Yes", "No", "B", "A", ...],
  "study_topics": ["Topic 1", "Topic 2", ...]
}
```

All 4 arrays must be the **same length** and **same order** as `evaluation_plan`:

- `questions` → `plan.map(p => p.question)`
- `correct_answers` → `plan.map(p => p.correct_answer)` (from the plan — `Yes`/`No` or `A`–`D`)
- `study_topics` → `plan.map(p => p.study_topic)`
- `answers` → the user’s choices, **same canonical values**: `Yes` | `No` | `A` | `B` | `C` | `D` (the API accepts common variants like `y`/`n` and normalizes them)

**Code:**
```javascript
async function getResults(plan, userAnswers) {
  const res = await fetch(`${API_URL}/interview-ready/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      questions: plan.map((p) => p.question),
      answers: userAnswers,
      correct_answers: plan.map((p) => p.correct_answer),
      study_topics: plan.map((p) => p.study_topic),
    }),
  });
  if (!res.ok) {
    alert("Something went wrong");
    return;
  }
  const data = await res.json();
  return data; // readiness_percentage, strengths, gaps, learning_recommendations
}
```

**What you get:**
```json
{
  "readiness_percentage": 73,
  "readiness_label": "Almost Ready",
  "strengths": ["Dependency Injection", "React Hooks"],
  "gaps": ["Singleton Thread Safety"],
  "learning_recommendations": [
    { "priority": "Critical", "topic": "Singleton Thread Safety", "why": "..." }
  ]
}
```

Show the percentage, label, strengths list, gaps list, and recommendations on your results page.

---

## Interview Readiness Plan (holistic — placement-aware)

**URL:** `POST your-api-url/interview-ready/interview-readiness/plan`

**Body:** `InterviewReadinessPlanRequest` — required: `user_type`, `primary_skill`. Optional: `experience_years`, `target_role`, `email`, `phone`, `college_name`, `assessment_focus`, `user_category`, and context fields below.

- **`user_category`** (optional): `3rd_year` | `4th_year` | `recent_graduate` | `working_professional`. If omitted, it is **inferred** from `user_type` (e.g. 3rd Year Student → `3rd_year`, 4th Year → `4th_year`, recent graduate → `recent_graduate`, working professional → `working_professional`).
- **1st–3rd year bucket:** only core fields; no placement extras required.
- **4th year / recent graduate:** optional `campus_or_off_campus`, `targets_service_mnc`, `targets_product_company`, `target_companies_notes`, `specific_role_requested`, `specific_role`.
- **Working professional:** optional `current_organization`, `core_skill`, `jd_provided`, `job_description`, `target_company_name`.

`primary_skill` may be a comma-separated list (up to 400 chars). **Response:** exactly 15 items in fixed order: 4× `yes_no`, 7× `multiple_choice`, 2× `scenario`, 2× `code_mcq` — each includes `explanation` (same shapes as skill-readiness plan; see OpenAPI `/docs`).

---

## Aptitude Readiness Plan (placement aptitude — engineering 4th year style)

**URL:** `POST your-api-url/interview-ready/aptitude-readiness/plan`

**Body:** `AptitudeReadinessPlanRequest` — required: `user_type`. Optional: `experience_years`, `primary_skill`, `target_role`, `target_company_type`, `email`, `phone`.

- `primary_skill` defaults to: `Quantitative, Logical and Verbal Reasoning`.
- `target_role` defaults to: `Software Engineer`.
- `target_company_type` defaults to: `both` (`service_mnc` | `product_company` | `both`).
- Response shape for this API is **15× `multiple_choice`** questions only (all with `section`, `options`, `correct_answer` as `A`-`D`, `study_topic`, `explanation`).
- Section split is server-enforced: **exactly 5 Quantitative, 5 Logical, 5 Verbal** (`section` values: `quantitative`, `logical`, `verbal`).
- Prompt is tuned for medium-level IT-company placement aptitude style (TCS/Infosys/Wipro/Cognizant/Capgemini/Accenture-like patterns).

---

## API 2: Inquiries (waitlist + contact)

**URL:** `POST your-api-url/api/inquiries`  
(Config: `VITE_API_URL` + path; override path only with `VITE_INQUIRIES_PATH`, default `/api/inquiries`.)

**Headers:** `Content-Type: application/json`

**Body:** Common shape; **`intent`** is required — `"waitlist"` or `"contact"`.

| Field | Type | Notes |
|-------|------|--------|
| `intent` | `"waitlist"` \| `"contact"` | Required |
| `source` | string | e.g. `waitlist_page`, `contact_page` |
| `submitted_at` | string (ISO-8601) | Client timestamp |
| `name` | string \| null | |
| `email` | string \| null | Waitlist may send `null` |
| `phone` | string \| null | |
| `college` | string \| null | Waitlist |
| `year` | string \| null | Waitlist (e.g. `"4th Year"`) |
| `target_role` | string \| null | Waitlist |
| `whatsapp_opt_in` | boolean \| null | Waitlist only |
| `message` | string \| null | Contact |
| `topic` | `"colleges"` \| null | Contact — from `?topic=` |
| `audience` | `"students"` \| `"colleges"` \| null | Contact |
| `score` | any \| null | Reserved |

**Validation (server):**

- **`intent === "contact"`:** require `name`, `email`, `phone`, `message` (non-empty after trim).
- **`intent === "waitlist"`:** require `name`, `phone`, `college`, `year`, `target_role` (non-empty after trim).

**Example — waitlist**
```json
{
  "intent": "waitlist",
  "source": "waitlist_page",
  "submitted_at": "2026-04-06T12:00:00.000Z",
  "name": "Priya",
  "email": null,
  "phone": "9876543210",
  "college": "IIT Delhi",
  "year": "4th Year",
  "target_role": "Software Engineer",
  "whatsapp_opt_in": true,
  "message": null,
  "topic": null,
  "audience": null,
  "score": null
}
```

**Example — contact**
```json
{
  "intent": "contact",
  "source": "contact_page",
  "submitted_at": "2026-04-06T12:00:00.000Z",
  "name": "Rahul",
  "email": "rahul@example.com",
  "phone": "+91 98765 43210",
  "college": null,
  "year": null,
  "target_role": null,
  "whatsapp_opt_in": null,
  "message": "I'd like to know more about mentorship.",
  "topic": null,
  "audience": "students",
  "score": null
}
```

**Success:** `{ "status": "ok", "message": "Thank you! We'll get back to you." }`

---

## Errors

| What happens | What to show user |
|--------------|-------------------|
| 422 | Show the `detail` message from response (e.g. "Please enter a valid technical skill") |
| 429 | "Too many requests. Wait a minute and try again." |
| 500 / 504 | "Something went wrong. Please try again." |

**How to read error:**
```javascript
if (!res.ok) {
  const data = await res.json().catch(() => ({}));
  const msg = data.detail || "Something went wrong";
  // if detail is array: data.detail[0].msg
  const message = Array.isArray(data.detail) ? data.detail[0]?.msg : msg;
  alert(message);
}
```

---

## Resume ATS check — overview for frontend (`POST /api/resume/ats`)

Use this for the **resume upload / ATS feedback** flow. The API returns **scores**, **keyword match lists**, and **coaching text** tuned for **Naukri + LinkedIn** visibility (when the server has LLM enrichment enabled).
#
### Purpose

- User picks a **target role** (e.g. “Software Engineer”) and uploads a **resume file**.
- Backend extracts text, computes **rule-based scores**, then (by default) calls **OpenAI** to write **summary**, **strengths**, **fixes**, and **portal_tips**.
- **Numeric scores are not from a real Greenhouse/Workday ATS** — treat them as directional (weak / OK / strong), not exact percentages.

### Request

| Item | Value |
|------|--------|
| **Method** | `POST` |
| **URL** | `{API_BASE}/api/resume/ats` |
| **Content-Type** | `multipart/form-data` (do **not** send JSON body) |
| **Rate limit** | 30 requests / minute / IP (see 429 handling below) |

**Form fields (required):**

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | Resume: **.pdf**, **.doc**, or **.docx** (use `file.name` as filename) |
| `target_role` | string | Selected role label, e.g. `"Software Engineer"`, `"Frontend Developer"` |

**Example (browser):**

```javascript
const formData = new FormData();
formData.append("file", file, file.name);
formData.append("target_role", roleLabel);

const res = await fetch(`${API_BASE}/api/resume/ats`, {
  method: "POST",
  body: formData,
});
const data = await res.json();
```

### Success response (`200`)

JSON object **shape**:

| Field | Type | What to show |
|-------|------|----------------|
| `score` | number (0–100) | Main overall score / gauge |
| `keywords` | number (0–100) | How well resume text matches **target_role** tokens |
| `formatting` | number (0–100) | Structure, sections, bullets, length signals |
| `impact` | number (0–100) | Metrics, action verbs, quantified outcomes |
| `ats` | number (0–100) | Parseability / ATS-friendly text signals |
| `summary` | string | Short narrative (often mentions scores + Naukri/LinkedIn when LLM is on) |
| `matched_keywords` | string[] | Terms from **target_role** found in the resume |
| `missing_keywords` | string[] | Terms from **target_role** **not** found (suggest adding where truthful) |
| `strengths` | string[] | **What’s already working** for recruiter search / screening |
| `fixes` | string[] | **Prioritized resume edits** (document content) |
| `portal_tips` | string[] | **Naukri + LinkedIn** checklist (headline, key skills, About, profile consistency, file format) |

**UI suggestion:** four sub-scores + overall `score`; separate sections for **Summary**, **Strengths**, **Fixes (resume)**, **Portal tips (Naukri & LinkedIn)**; chips for matched/missing keywords.

**Example (truncated):**

```json
{
  "score": 72,
  "keywords": 65,
  "formatting": 80,
  "impact": 70,
  "ats": 78,
  "summary": "...",
  "matched_keywords": ["software", "engineering"],
  "missing_keywords": ["react"],
  "strengths": ["..."],
  "fixes": ["..."],
  "portal_tips": ["..."]
}
```

### Errors

| Status | Meaning |
|--------|---------|
| **422** | Bad file type, unreadable file, empty `target_role`, or almost no extractable text |
| **413** | File larger than **5 MB** |
| **429** | Too many requests — show “try again in a minute” |
| **500** | Server error — generic retry message |

Read `detail` from JSON error body when present.

### Backend notes (for transparency)

- **Scores** (`score`, `keywords`, `formatting`, `impact`, `ats`) are **computed on the server** (heuristics), not by the LLM.
- **`server` env `RESUME_ATS_USE_LLM`:** when `true` (default), **summary / strengths / fixes / portal_tips** are LLM-enriched; if the LLM fails, the API still returns **200** with heuristic text + default portal tips.
- **`portal_tips`** is always present (may be rule-based only if LLM is off or fails).

### OpenAPI

Interactive docs: **`GET /docs`** on the API host → **`POST /api/resume/ats`**.

---

## Summary

| Page / Action | API to call |
|---------------|-------------|
| Interview Ready: user submits profile | `POST /interview-ready/plan` |
| Interview Readiness (holistic) | `POST /interview-ready/interview-readiness/plan` |
| Aptitude Readiness (placement aptitude) | `POST /interview-ready/aptitude-readiness/plan` |
| Interview Ready: user submits answers | `POST /interview-ready/evaluate` |
| Waitlist or contact form | `POST /api/inquiries` |
| Resume upload / ATS-style feedback | `POST /api/resume/ats` |

**Tip:** Replace `https://your-api.railway.app` with your real API URL.
