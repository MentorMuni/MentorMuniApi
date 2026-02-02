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

Generates 15 role-specific Yes/No questions based on the user’s profile: 7 topic checks + 8 complex scenario-based interview questions.

### Request

```
POST /interview-ready/plan
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `user_type` | string | Yes | `"student"` or `"working professional"` |
| `experience_years` | number | Yes | 0–50 |
| `primary_skill` | string | Yes | 1–100 chars (e.g., `.NET`, `React`, `Data Science`) |
| `target_role` | string | Yes | 1–100 chars (e.g., `Backend Developer`) |

**Example:**

```json
{
  "user_type": "working professional",
  "experience_years": 3,
  "primary_skill": "React",
  "target_role": "Frontend Developer"
}
```

### Response

**Success (200 OK):**

```json
{
  "evaluation_plan": [
    "Can you explain React hooks (useState, useEffect)?",
    "Have you worked with state management (Redux, Context)?",
    "Can you optimize React performance (memoization, lazy loading)?"
  ]
}
```

`evaluation_plan` is an array of 15 Yes/No questions in the same order you should display and collect answers. First 7 are topic checks; next 8 are scenario-based questions that require deeper knowledge.

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
| `questions` | string[] | Yes | Non-empty; same length as `answers` |
| `answers` | string[] | Yes | Each value is `"Yes"` or `"No"` |

The order of `questions` and `answers` must match the order returned from `/interview-ready/plan`.

**Example:**

```json
{
  "questions": [
    "Can you explain React hooks (useState, useEffect)?",
    "Have you worked with state management (Redux, Context)?",
    "Can you optimize React performance (memoization, lazy loading)?"
  ],
  "answers": ["Yes", "No", "Yes"]
}
```

### Response

**Success (200 OK):**

```json
{
  "readiness_percentage": 67,
  "readiness_label": "Almost Ready",
  "strengths": [
    "Can explain React hooks (useState, useEffect)",
    "Can optimize React performance (memoization, lazy loading)"
  ],
  "gaps": [
    "State management (Redux, Context)"
  ],
  "learning_recommendations": [
    {
      "priority": "High",
      "topic": "State management (Redux, Context)",
      "why": "Core skill for frontend roles"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `readiness_percentage` | int | 0–100 score |
| `readiness_label` | string | `"Not Ready"`, `"Almost Ready"`, or `"Interview Ready"` |
| `strengths` | string[] | Topics the user answered “Yes” to |
| `gaps` | string[] | Topics the user answered “No” to |
| `learning_recommendations` | array | Items with `priority`, `topic`, `why` (e.g., Critical, High, Medium, Optional) |

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
      user_type: profile.userType,      // "student" | "working professional"
      experience_years: profile.years,
      primary_skill: profile.skill,
      target_role: profile.role,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.evaluation_plan; // array of questions
}

// Step 2: Evaluate readiness
async function evaluate(questions, answers) {
  const res = await fetch(`${API_BASE}/interview-ready/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ questions, answers }),
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
