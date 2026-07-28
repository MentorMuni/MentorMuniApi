# MentorMuni API

MentorMuni is an AI-driven mentorship platform. This API is built with FastAPI.

## Features
- Interview / skill / aptitude / AI readiness plan generation (OpenAI)
- Voice interview session + analysis
- Resume ATS scoring
- Health check and environment-based configuration
- Phase 1 foundation: async Postgres (SQLAlchemy 2 + asyncpg + Alembic)

## Setup

1. Clone the repository and enter the project directory:
   ```bash
   cd MentorMuniAPI
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file from `.env.example` and set:
   - `OPENAI_API_KEY` (AI endpoints)
   - `DATABASE_URL` (Postgres; Railway injects this in production)
   - `API_KEY` (long random secret; frontend sends as `X-API-Key`)

   Generate an API key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

4. Apply database migrations (from `mentormuni-api/`):
   ```bash
   cd mentormuni-api
   alembic upgrade head
   ```

   This creates the 7 Phase 1 tables and seeds roles, MentorMuni Public org, and starter plans.

5. Run the application (from repo root):
   ```bash
   cd mentormuni-api && PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. Open the interactive docs:
   ```
   http://127.0.0.1:8000/docs
   ```

## Phase 1 schema (7 tables)

`organizations` → `subscription_plans` / `organization_subscriptions` / `organization_features` / `departments` / `users`  
`roles` (lookup by `role_code`, never by id)
