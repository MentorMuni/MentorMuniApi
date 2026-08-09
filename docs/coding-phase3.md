# Coding assessment — Phase 3

## Endpoints (`/api/coding`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/assessments` | List available active assessments |
| GET | `/assessments/{id_or_slug}` | Assessment summary |
| POST | `/assessments/{id_or_slug}/start` | Idempotent start + snapshot |
| GET | `/attempts/{attempt_id}` | Attempt + frozen problem list + timer |
| GET | `/attempts/{attempt_id}/problems/{problem_id}` | Student-safe versioned problem |
| PUT | `/attempts/{attempt_id}/problems/{problem_id}/draft` | Upsert draft |
| GET | `/attempts/{attempt_id}/problems/{problem_id}/draft?language=` | Get draft |

Auth: existing `X-API-Key` + student JWT (`require_roles(STUDENT)`).

## Attempt states (Phase 2 enums)

- `in_progress` — active
- `submitted` — reserved for later submit phase
- `expired` — server-side when `ends_at` passed
- Conceptual `not_started` = no attempt row yet

## Not in Phase 3

Judge0, execution, scoring, OpenAI, Monaco widget.

## Migrate

```bash
cd mentormuni-api && PYTHONPATH=. alembic upgrade head
# includes 0017 schema+seed and 0018 active-attempt unique index
```

## Tests

```bash
cd mentormuni-api
PYTHONPATH=. pytest tests/test_coding_phase3_unit.py -q
PYTHONPATH=. pytest tests/test_coding_phase3_integration.py -q   # needs Postgres + migrations
```
