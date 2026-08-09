# Coding assessment — Phase 2 notes

## What shipped in Phase 2

- Domain package `app/coding/`
- Versioned schema (`coding_problems` + immutable `coding_problem_versions`)
- Attempt snapshot tables (used in Phase 3+)
- Durable `coding_jobs` (worker comes in Phase 4 — not BackgroundTasks)
- Append-only `coding_runs` for future iteration analytics
- Configurable limits via `Settings` + `app/coding/limits.py`
- Seed: languages python/cpp/java, **Two Sum** problem v1, practice assessment `practice-two-sum`
- **No AI question generation** — content is pre-authored and served at runtime

## Migrate

```bash
cd mentormuni-api
PYTHONPATH=. alembic upgrade head
```

## Review checklist before Phase 3

- [ ] Migration applies cleanly
- [ ] Seed assessment slug `practice-two-sum` exists
- [ ] Hidden tests exist; reference solution not for student APIs
- [ ] Official score column on submissions is separate from AI coaching tables
