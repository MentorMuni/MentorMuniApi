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
  "user_type": "Working Professional",
  "primary_skill": "React"
}
```

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
      user_type: profile.userType,      // "3rd Year Student" or "4th Year Student" or "Working Professional"
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

- Loop over `evaluation_plan`
- Show each `item.question` with Yes and No buttons
- Save user's answers in order: `["Yes", "No", "Yes", ...]`

---

### Part C: Get Results (when user clicks "See My Results")

**URL:** `POST your-api-url/interview-ready/evaluate`

**Send this:** Use the saved plan + user answers.

```json
{
  "questions": ["question 1", "question 2", ...],
  "answers": ["Yes", "No", ...],
  "correct_answers": ["Yes", "No", ...],
  "study_topics": ["Topic 1", "Topic 2", ...]
}
```

All 4 arrays must be in the same order. Get them from the plan:
- `questions` = `plan.map(p => p.question)`
- `correct_answers` = `plan.map(p => p.correct_answer)`
- `study_topics` = `plan.map(p => p.study_topic)`
- `answers` = user's choices

**Code:**
```javascript
async function getResults(plan, userAnswers) {
  const res = await fetch(`${API_URL}/interview-ready/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      questions: plan.map(p => p.question),
      answers: userAnswers,
      correct_answers: plan.map(p => p.correct_answer),
      study_topics: plan.map(p => p.study_topic)
    })
  });
  if (!res.ok) {
    alert("Something went wrong");
    return;
  }
  const data = await res.json();
  return data;  // has readiness_percentage, strengths, gaps, learning_recommendations
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

## API 2: Contact Form (when user clicks Submit)

**URL:** `POST your-api-url/contact/submit`

**Send this:**
```json
{
  "name": "Rahul",
  "email": "rahul@example.com",
  "phone": "9146421302",
  "message": "Interested in your courses"
}
```

`year` and `message` are optional.

**Code:**
```javascript
async function submitContact(form) {
  const res = await fetch(`${API_URL}/contact/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: form.name,
      email: form.email,
      phone: form.phone,
      year: form.year || null,
      message: form.message || null
    })
  });
  if (!res.ok) {
    alert("Could not submit. Try again.");
    return;
  }
  const data = await res.json();
  alert(data.message);  // "Thank you! We'll get back to you."
}
```

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

## Summary

| Page / Action | API to call |
|---------------|-------------|
| Interview Ready: user submits profile | `POST /interview-ready/plan` |
| Interview Ready: user submits answers | `POST /interview-ready/evaluate` |
| Contact: user submits form | `POST /contact/submit` |

**Tip:** Replace `https://your-api.railway.app` with your real API URL.
