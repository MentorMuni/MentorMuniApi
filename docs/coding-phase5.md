# Coding assessment — Phase 5 (Run Code API)

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/coding/runs` | Enqueue public-test run (`coding_runs` + `coding_jobs`) |
| GET | `/api/coding/runs/{run_id}` | Poll execution status / public case summary |

Auth: student JWT + API key.

## Flow

Student → POST `/runs` → FastAPI validates + inserts run/job → returns immediately  
Worker → Judge0 (public tests only) → updates `coding_runs`  
Student → poll GET `/runs/{id}`

No OpenAI. No hidden tests. No official score.

## Request

```json
{
  "attempt_id": 1,
  "problem_id": 1,
  "language_code": "python",
  "source_code": "..."
}
```

## Next

Phase 6: Submit + hidden tests + deterministic scoring
