# Frontend Changes Required

Summary of what needs to change on the frontend (MentorMuniUI) to integrate with the API.

---

## 1. API Base URL

Set the API base URL somewhere global (e.g. in a config or before scripts load):

```javascript
// Option A: In HTML before script
window.MENTORMUNI_API_BASE = "https://your-api.railway.app";  // or http://localhost:8000 for local

// Option B: In interview-ready.js / app.js
const API_BASE = window.MENTORMUNI_API_BASE || "https://your-api.railway.app";
```

---

## 2. Contact Page (`contact.html` + `app.js`)

**Current:** Form submits to Google Apps Script (`GAS_URL`).

**Change:** Submit to `POST /contact/submit` instead.

### In `app.js` – Contact form handler

Replace the `fetch(GAS_URL, ...)` block with:

```javascript
const API_BASE = window.MENTORMUNI_API_BASE || "https://your-api.railway.app";

// In contactForm submit handler:
const res = await fetch(`${API_BASE}/contact/submit`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: name.trim(),
    email: email.trim(),
    phone: phone.trim(),
    year: null,  // optional – add a "Year" field to form if needed
    message: (contactForm.querySelector("[name='query']")?.value || "").trim() || null
  })
});

if (res.ok) {
  const data = await res.json();
  alert(data.message || "Thank you! We'll get back to you.");
  contactForm.reset();
} else {
  const err = await res.json().catch(() => ({}));
  alert(err.detail || "Submission failed. Please try again.");
}
```

**Note:** The form uses `name="query"` for the message; the API expects `message`. Map `query` → `message` as above.

---

## 3. Interview Ready Page (`interview-ready.html` + `interview-ready.js`)

**Note:** `interview-ready.html` may not exist yet. Create it if missing, and add `interview-ready.js` for API calls.

### Step 1: Profile form → Plan API

**Request payload (matches UI form):**

```javascript
{
  user_type: "3rd Year Student" | "4th Year Student" | "Working Professional",
  primary_skill: "React",  // from "Primary tech stack" input
  email: "user@example.com",  // optional
  phone: "9146421302"        // optional
}
```

**No need to send** `experience_years` or `target_role` – API uses defaults.

**Response:** `{ evaluation_plan: [ { question, correct_answer, study_topic }, ... ] }`

**Store** the full `evaluation_plan` array (you need `correct_answer` and `study_topic` for Evaluate).

### Step 2: Questions → Collect answers

- Show each `item.question`
- User selects Yes or No
- Keep answers in the same order as `evaluation_plan`

### Step 3: Submit → Evaluate API

```javascript
{
  questions: plan.map(p => p.question),
  answers: userAnswers,           // ["Yes", "No", "Yes", ...]
  correct_answers: plan.map(p => p.correct_answer),
  study_topics: plan.map(p => p.study_topic)
}
```

**Response:** `{ readiness_percentage, readiness_label, strengths, gaps, learning_recommendations }`

### Display results

- `readiness_percentage` – circular/percentage display
- `readiness_label` – "Not Ready" | "Almost Ready" | "Interview Ready"
- `strengths` – list of topic strings
- `gaps` – list of topic strings
- `learning_recommendations` – `{ priority, topic, why }[]`

---

## 4. Error Handling

| Status | Action |
|--------|--------|
| 422 | Show validation error from `detail` (array or string) |
| 429 | "Too many requests. Please wait a moment." |
| 504 | "Request timed out. Please try again." |
| 500 | "Something went wrong. Please try again." |

---

## 5. Admin Endpoints (View Stored Data)

```
GET /admin/submissions   → contact form submissions
GET /admin/leads         → Interview Ready leads (email/phone from plan)
?limit=100 (optional, default 100)
```

**Example:**
```bash
curl "https://your-api.railway.app/admin/submissions"
curl "https://your-api.railway.app/admin/leads?limit=50"
```

---

## 6. Checklist

- [ ] Set `MENTORMUNI_API_BASE` (or equivalent) to your Railway API URL
- [ ] Contact form: Change from Google Apps Script to `POST /contact/submit`
- [ ] Contact form: Map `query` → `message`
- [ ] Interview Ready: Create page + JS if missing
- [ ] Interview Ready: Profile → `POST /interview-ready/plan` with `user_type`, `primary_skill`, `email`, `phone`
- [ ] Interview Ready: Store full `evaluation_plan` (question, correct_answer, study_topic)
- [ ] Interview Ready: Evaluate → `POST /interview-ready/evaluate` with `questions`, `answers`, `correct_answers`, `study_topics`
- [ ] Interview Ready: Show results (%, label, strengths, gaps, learning_recommendations)
