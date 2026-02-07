# API Schemas for UI Integration

Use these schemas to integrate the Interview Readiness APIs with your frontend.

---

## 1. Plan API

### Request: `POST /interview-ready/plan`

```typescript
interface PlanRequest {
  user_type: string;         // "3rd Year Student" | "4th Year Student" | "Working Professional" or "student" | "working professional"
  primary_skill: string;     // required, e.g. "React", ".NET"
  experience_years?: number; // optional, default 0 (0-50)
  target_role?: string;      // optional, defaults to "{primary_skill} Developer"
  email?: string | null;     // optional; omit, null, or "" = not provided (no lead capture)
  phone?: string | null;     // optional; omit, null, or "" = not provided (no lead capture)
}
```

**Minimal payload (matches UI):**

```json
{
  "user_type": "Working Professional",
  "primary_skill": ".NET",
  "email": "user@example.com",
  "phone": "9146421302"
}
```

### Response: `200 OK`

```typescript
interface PlanResponse {
  evaluation_plan: QuestionItem[];
}

interface QuestionItem {
  question: string;           // Display this to user
  correct_answer: "Yes" | "No";  // Do NOT show — used for scoring
  study_topic: string;        // Short topic name (e.g. "Dependency Injection")
}
```

**Example:**

```json
{
  "evaluation_plan": [
    {
      "question": "Can you explain how dependency injection improves testability in large systems?",
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

---

## 2. Evaluate API

### Request: `POST /interview-ready/evaluate`

Build this from the Plan response + user's answers. All arrays must be in the same order (by index).

```typescript
interface EvaluateRequest {
  questions: string[];       // From plan: item.question
  answers: string[];         // User's choices: "Yes" | "No" each
  correct_answers: string[]; // From plan: item.correct_answer
  study_topics: string[];    // From plan: item.study_topic
}
```

**Example:**

```json
{
  "questions": [
    "Can you explain how dependency injection improves testability?",
    "In React, state updates are always synchronous. Yes or No?"
  ],
  "answers": ["Yes", "No"],
  "correct_answers": ["Yes", "No"],
  "study_topics": ["Dependency Injection", "React State Batching"]
}
```

### Response: `200 OK`

```typescript
interface EvaluateResponse {
  readiness_percentage: number;   // 0-100
  readiness_label: string;        // "Not Ready" | "Almost Ready" | "Interview Ready"
  strengths: string[];            // Topics user got right
  gaps: string[];                 // Topics user got wrong (to study)
  learning_recommendations: LearningRecommendation[];
}

interface LearningRecommendation {
  priority: "Critical" | "High" | "Medium" | "Optional";
  topic: string;                  // Study topic
  why: string;                    // Reason/guidance
}
```

**Example:**

```json
{
  "readiness_percentage": 73,
  "readiness_label": "Almost Ready",
  "strengths": [
    "Dependency Injection",
    "Async/Await Patterns",
    "Database Indexing"
  ],
  "gaps": [
    "React State Batching",
    "Singleton Thread Safety"
  ],
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

---

## 3. UI Flow

```
1. User fills profile → POST /interview-ready/plan
2. Store evaluation_plan (full array)
3. Show each item.question with Yes/No buttons
4. Collect user answers in same order
5. POST /interview-ready/evaluate with:
   - questions: plan.map(p => p.question)
   - answers: userAnswers
   - correct_answers: plan.map(p => p.correct_answer)
   - study_topics: plan.map(p => p.study_topic)
6. Display EvaluateResponse: %, label, strengths, gaps, learning_recommendations
```

---

## 4. Contact Submit (File Storage)

### Request: `POST /contact/submit`

Stores contact/enroll details in a JSONL file (no database).

```typescript
interface ContactSubmitRequest {
  name: string;      // required
  email: string;     // required, valid email
  phone: string;     // required, 8-20 chars
  year?: string;     // optional, e.g. "3rd year", "Final year"
  message?: string;  // optional
}
```

**Example:**

```json
{
  "name": "Rahul",
  "email": "rahul@example.com",
  "phone": "9146421302",
  "year": "3rd year",
  "message": "Interested in React course"
}
```

**Response:** `200 OK` → `{ "status": "ok", "message": "Thank you! We'll get back to you." }`

**Storage:** Data is appended to `contact_submissions.jsonl` (path: `DATA_DIR` env or `/tmp`).

---

## 5. Error Responses

All endpoints return `422` for validation errors:

```typescript
interface ValidationError {
  detail: Array<{
    type: string;
    loc: string[];   // e.g. ["body", "answers", 1]
    msg: string;
  }> | string;
}
```

| Status | Meaning |
|--------|---------|
| 422 | Invalid input (wrong types, empty fields, length mismatch) |
| 429 | Rate limit exceeded |
| 504 | Plan API: LLM timeout |
| 500 | Server error |
