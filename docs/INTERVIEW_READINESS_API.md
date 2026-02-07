# Interview Readiness API Documentation

Use these two endpoints from your frontend (e.g., mentormuni.com) to power the “Am I Interview Ready?” flow.

---

## Base URL

| Environment | Base URL |
|-------------|----------|
| Local | `http://localhost:8000` |
| Railway (production) | `https://your-app-name.railway.app` |

Replace with your actual Railway URL after deployment.

---

## CORS

**Yes, CORS is required** when the frontend and API run on different origins (e.g., `mentormuni.com` calling `your-api.railway.app`).

CORS is already configured on the API:

- `allow_origins=["*"]` – allows requests from any origin
- For production, consider restricting to `["https://mentormuni.com", "https://www.mentormuni.com"]` in `main.py`

---

## Authentication

No API key or auth header is required. Rate limiting is applied per IP:

- **Plan**: 20 requests/minute per IP  
- **Evaluate**: 60 requests/minute per IP  

---

## Endpoint 1: Generate Interview Plan

Generates 15 role-specific Yes/No questions based on the user’s profile: Each item has question, correct_answer, and study_topic.

### Request

```
POST /interview-ready/plan
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `user_type` | string | Yes | `"student"`, `"working professional"`, `"3rd Year Student"`, `"4th Year Student"` |
| `primary_skill` | string | Yes | 1–100 chars (e.g., `.NET`, `React`) |
| `experience_years` | number | No | Default 0; 0–50 |
| `target_role` | string | No | Defaults to `"{primary_skill} Developer"` |
| `email` | string | No | Optional; stored for lead capture |
| `phone` | string | No | Optional; stored for lead capture |

**Example (full):**

```json
{
  "user_type": "Working Professional",
  "primary_skill": "React",
  "experience_years": 3,
  "target_role": "Frontend Developer",
  "email": "user@example.com",
  "phone": "9146421302"
}
```

**Example (minimal – matches UI form):**

```json
{
  "user_type": "3rd Year Student",
  "primary_skill": ".NET",
  "email": "user@example.com",
  "phone": "9146421302"
}
```

### Response

**Success (200 OK):**

```json
{
  "evaluation_plan": [
    {
      "question": "Can you explain how dependency injection improves testability?",
      "correct_answer": "Yes",
      "study_topic": "Dependency Injection"
    },
    {
      "question": "In React, state updates are always synchronous. Yes or No?",
      "correct_answer": "No",
      "study_topic": "React State Batching"
    }
  ]
}
```

`evaluation_plan` is an array of 15 objects. Each has `question` (to display), `correct_answer` (Yes or No — do not show to user), and `study_topic` (short topic name for strengths/gaps/recommendations). Store all three for the Evaluate call.

### Error responses

| Status | Meaning |
|--------|---------|
| 422 | Validation error (e.g., invalid `user_type`, out-of-range `experience_years`) |
| 429 | Rate limit exceeded |
| 504 | LLM timeout |
| 500 | Server error |

**Example 422:**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "user_type"],
      "msg": "Value error, user_type must be 'student' or 'working professional'"
    }
  ]
}
```

---

## Endpoint 2: Evaluate Readiness

Evaluates the user’s answers and returns readiness %, strengths, gaps, and a prioritized learning roadmap.

### Request

```
POST /interview-ready/evaluate
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `questions` | string[] | Yes | Same order as Plan response |
| `answers` | string[] | Yes | User's answers: `"Yes"` or `"No"` each |
| `correct_answers` | string[] | Yes | From Plan response; same order |
| `study_topics` | string[] | Yes | From Plan response; same order (for strengths/gaps) |

All four arrays must have the same length.

**Example:**

```json
{
  "questions": ["Can you explain DI?", "In React, state updates are synchronous. Yes or No?"],
  "answers": ["Yes", "No"],
  "correct_answers": ["Yes", "No"],
  "study_topics": ["Dependency Injection", "React State Batching"]
}
```

### Response

**Success (200 OK):**

```json
{
  "readiness_percentage": 67,
  "readiness_label": "Almost Ready",
  "strengths": ["Dependency Injection", "React Hooks"],
  "gaps": ["React State Batching", "Singleton Thread Safety"],
  "learning_recommendations": [
    {
      "priority": "Critical",
      "topic": "React State Batching",
      "why": "Core topic essential for your target role."
    },
    {
      "priority": "High",
      "topic": "Singleton Thread Safety",
      "why": "Important for technical interviews."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `readiness_percentage` | int | 0–100 score (correct answers / total) |
| `readiness_label` | string | `"Not Ready"`, `"Almost Ready"`, or `"Interview Ready"` |
| `strengths` | string[] | Study topics the user got right |
| `gaps` | string[] | Study topics the user got wrong (areas to improve) |
| `learning_recommendations` | array | Prioritized topics to study (Critical, High, Medium, Optional) with `topic` and `why` |

### Error responses

| Status | Meaning |
|--------|---------|
| 422 | Validation error (empty answers, invalid values, length mismatch) |
| 429 | Rate limit exceeded |
| 500 | Server error |

**Example 422:**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "answers", 1],
      "msg": "Value error, answer at index 1 must be 'Yes' or 'No', got: 'Maybe'"
    }
  ]
}
```

---

## Frontend integration example

```javascript
const API_BASE = "https://your-api.railway.app"; // or http://localhost:8000

// Step 1: Generate plan
async function getPlan(profile) {
  const res = await fetch(`${API_BASE}/interview-ready/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_type: profile.userType,
      experience_years: profile.years,
      primary_skill: profile.skill,
      target_role: profile.role,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.evaluation_plan; // [{ question, correct_answer, study_topic }, ...]
}

// Step 2: Evaluate readiness (pass all arrays from Plan + user answers)
async function evaluate(plan, userAnswers) {
  const res = await fetch(`${API_BASE}/interview-ready/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      questions: plan.map((p) => p.question),
      answers: userAnswers,
      correct_answers: plan.map((p) => p.correct_answer),
      study_topics: plan.map((p) => p.study_topic),
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

---

## Health check

For monitoring and uptime checks:

```
GET /health
```

Returns:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-02T12:00:00.000Z",
  "version": "1.0.0"
}
```
