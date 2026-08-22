# Backend: Student Week-1 roadmap + 90-day placement plan

**Audience:** Frontend / student portal  
**Base:** API key + student JWT (`Authorization: Bearer`)  
**Prefix:** `/student/roadmap`

## Week-1 baseline (sequential unlock)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/student/roadmap` | Seeds Week 1 on first call; returns steps with `locked` / `current` / `done` |
| POST | `/student/roadmap/steps/{tool_code}/complete` | Body: score, label, strengths, weaknesses, recommendations, raw. Rejects locked steps (409). |
| GET | `/student/roadmap/analysis` | Aggregated scores, top strengths/weaknesses |
| GET | `/student/roadmap/results?tool_code=` | Attempt history |
| GET | `/student/roadmap/progress` | Activity + analysis + cached learning topics (if generated) |
| POST | `/student/roadmap/progress/learning-topics` | OpenAI topics for weak points + nearby areas; persists on the week |

### tool_code order

`5_sec` → `aptitude` → `skill_readiness` → `skill_mock` → `project_mock` → `interview_readiness` → `interview_mock` → `hr_mock`

Week `status=done` only when all 8 are `done`. Completing a step does **not** call OpenAI.

### Complete body example

```json
{
  "score": 72,
  "label": "Almost Ready",
  "technical_score": null,
  "communication_score": null,
  "strengths": ["Quant basics"],
  "weaknesses": ["Verbal inference"],
  "recommendations": ["Practice RC sets"],
  "raw": {}
}
```

## 90-day plan (after baseline done)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/student/roadmap/generate` | Requires week done. Returns immediately with `status=generating`. OpenAI runs in a background task (`placement_90day_v1`). Poll `GET /plan`. Idempotent while a non-stale generation is in flight; a `generating` row older than 5 minutes is marked `failed` so the student can retry. |
| GET | `/student/roadmap/plan` | Latest plan (`generating` / `ready` / `failed` / `superseded`) |
| GET | `/student/roadmap/plan/{id}` | By id |

Hard calendar in generated JSON: **Days 1–42 prep** (6 weeks) + **Days 43–90 AI mocks only**. Mock-phase days must reference an AI mock tool via week/day `focus_tools` or a `tool_href` containing `voice-interview`.

Week-1 AI voice mocks (`skill_mock`, `project_mock`, `interview_mock`, `hr_mock`) are each **20 minutes** in `WEEK1_STEPS`.

## Migration

`alembic upgrade head` → `0013_student_roadmap`

Tables: `student_roadmap_weeks`, `student_roadmap_steps`, `student_assessment_results`, `student_generated_roadmaps`.
