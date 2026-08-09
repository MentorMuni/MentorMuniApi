# Coding assessment — Phase 4 (code execution infrastructure)

## What shipped

- `CodeExecutionService` + `Judge0Provider` (async create/poll, status mapping)
- Postgres job queue: enqueue / claim (`SKIP LOCKED`) / retry / dead / stale recovery
- Dedicated worker: `python -m app.coding.worker` (Procfile `worker` entry)
- Run-job handler: loads public tests, executes via Judge0, persists `coding_runs` result
- Configurable limits already in Settings (+ `CODING_JOB_STALE_SECONDS`, `CODING_EXECUTION_PROVIDER`)

## Not in Phase 4

- Run Code HTTP API (Phase 5)
- Submit + hidden tests + scoring (Phase 6)
- Monaco / OpenAI / results UX / company intel (Phases 7–10)

## Run worker (Railway)

1. Set `JUDGE0_BASE_URL`, `JUDGE0_API_KEY`, `DATABASE_URL`
2. Start a second service with start command:
   `cd mentormuni-api && PYTHONPATH=. python -m app.coding.worker`

## Tests

```bash
cd mentormuni-api
PYTHONPATH=. pytest tests/test_coding_phase4_execution.py -q
```

## Phase map (current)

4 Code execution ← this phase  
5 Run Code API  
6 Submit + hidden tests + deterministic scoring  
7 Monaco coding screen  
8 OpenAI analysis  
9 Student learning/result experience  
10 Company-specific intelligence  
