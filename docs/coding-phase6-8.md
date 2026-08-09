# Coding assessment — Phase 6 (Submit + scoring) & Phase 8 (AI analysis)

## Phase 6 endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/coding/submissions` | Immutable submit; enqueue `submit_evaluate` |
| GET | `/api/coding/submissions/{id}` | Poll official score + public/hidden pass counts |

Auth: student JWT + API key.

## Official score

`official_score = 100 * (Σ passed weights / Σ all weights)`

- Computed only from Judge0 test results (public + hidden)
- Never influenced by OpenAI
- Hidden case I/O never returned to the client

## Phase 8

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/coding/submissions/{id}/analysis` | Coaching analysis when ready |

Worker flow after evaluate succeeds → enqueue `analyze` → `coding_ai_analyses`.

- AI failure leaves `official_score` intact (`analysis_status=failed`)
- Coaching scores are separate fields; UI must not treat them as the grade

## Next

Phase 7/9: Monaco widget + results UX (frontend)
Phase 10: company placement blurbs on assessment/attempt payloads
