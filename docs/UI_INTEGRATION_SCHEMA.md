# API Schemas for UI Integration

Use these schemas to integrate the Interview Readiness APIs with your frontend.

---

## 1. Plan API

### Request: `POST /interview-ready/plan`

```typescript
interface PlanRequest {
  user_type: "student" | "working professional";
  experience_years: number;  // 0-50
  primary_skill: string;     // e.g. "React", ".NET", "Data Science"
  target_role: string;       // e.g. "Frontend Developer"
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

## 4. Error Responses

Both endpoints return `422` for validation errors:

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
