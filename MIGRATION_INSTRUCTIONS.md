# Know Me Feature - PostgreSQL Migration Instructions

## Current Status
✅ Feature code: COMPLETE
✅ Database models: DEFINED  
✅ API endpoints: IMPLEMENTED
✅ Frontend UI: IMPLEMENTED  
⏳ **Database tables: PENDING MIGRATION**

---

## What Needs to be Done

The Know Me feature requires **4 private database tables** to be created in PostgreSQL:

1. `private_student_checkins` - Track check-in sessions
2. `private_student_responses` - Store student responses to questions
3. `private_student_insights` - Store AI-generated insights
4. `private_student_progress` - Track progress metrics

---

## Step-by-Step Migration

### Option 1: Using Alembic (Recommended)

#### Step 1: Provide PostgreSQL URL
Update your `.env` file with your PostgreSQL connection:

```bash
# Edit .env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database_name
```

**Where to get this:**
- Local PostgreSQL: `postgresql+asyncpg://postgres:password@localhost:5432/mentormuni`
- Railway: Check your Railway dashboard → Database → Connection URL
- AWS RDS: Check your RDS instance details
- Cloud provider: Check your database connection string

#### Step 2: Run Migration
```bash
cd /Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api
../.venv/bin/alembic upgrade head
```

#### Step 3: Verify
```bash
# Check tables were created (using psql)
psql -U your_user -d your_database -c "\dt private_*"

# Should show:
# private_student_checkins
# private_student_responses  
# private_student_insights
# private_student_progress
```

---

### Option 2: Manual SQL

If Alembic fails, copy/paste this SQL directly into your PostgreSQL client:

```sql
-- Table 1: Check-in sessions
CREATE TABLE private_student_checkins (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL
);
CREATE INDEX ix_psc_student_id_created ON private_student_checkins(student_id, created_at);

-- Table 2: Student responses
CREATE TABLE private_student_responses (
    id SERIAL PRIMARY KEY,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    question_key VARCHAR(128) NOT NULL,
    response_type VARCHAR(32) NOT NULL,
    response_value JSONB NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_psr_checkin_id ON private_student_responses(checkin_id);

-- Table 3: AI insights
CREATE TABLE private_student_insights (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    source VARCHAR(32) NOT NULL DEFAULT 'openai',
    model VARCHAR(64) NULL,
    headline TEXT NOT NULL,
    what_i_hear JSONB NOT NULL DEFAULT '[]'::jsonb,
    blockers JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_plan JSONB NOT NULL DEFAULT '[]'::jsonb,
    full_insight_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_psi_student_id_created ON private_student_insights(student_id, created_at);

-- Table 4: Progress tracking
CREATE TABLE private_student_progress (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    metric_key VARCHAR(64) NOT NULL,
    value_before INTEGER NULL,
    value_after INTEGER NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_psp_student_id_created ON private_student_progress(student_id, created_at);
```

---

## Configuration After Migration

### 1. Update `.env`

```bash
# Database (already done above)
DATABASE_URL=postgresql+asyncpg://...

# OpenAI for Know Me insights
OPENAI_API_KEY=sk-...

# Model for Know Me AI (optional, defaults to gpt-4.1)
KNOW_MY_FEAR_MODEL=gpt-4.1

# API key (should already be set)
API_KEY=...

# Environment
APP_ENV=development
```

### 2. Start API

```bash
cd /Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api
set -a && source ../.env && set +a
PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Test Know Me Endpoint

```bash
# Start a check-in
curl -X POST http://127.0.0.1:8000/student/know-me/start \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Authorization: Bearer demo.student.test123"

# Should return:
# { "checkin_id": 1, "questions": [...], "total_steps": 8 }
```

---

## Troubleshooting

### Error: "connection refused" or "host is unreachable"
- ❌ PostgreSQL is not running or not accessible
- ✅ Check PostgreSQL is running: `psql -U postgres -c "SELECT version()"`
- ✅ Verify DATABASE_URL is correct

### Error: "unknown function: now()"
- ❌ You're still using SQLite (`sqlite://`)
- ✅ Update `.env` to use `postgresql+asyncpg://`

### Error: "FATAL: database does not exist"
- ❌ The database name in DATABASE_URL doesn't exist
- ✅ Create it first: `psql -U postgres -c "CREATE DATABASE mentormuni"`

### Migration succeeds but tables don't appear
- ❌ Alembic created them but you're checking the wrong database
- ✅ Verify DATABASE_URL matches your psql connection

### API starts but Know Me endpoint returns 500
- ❌ Tables don't exist in the database
- ✅ Run migration again and verify with `\dt private_*`

---

## Migration File Reference

**Location**: `/Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api/alembic/versions/0020_private_student_checkins.py`

**Migration ID**: `0020_private_student_checkins`

**Depends On**: `0019_coding_question_bank`

**Tables Created**:
- `private_student_checkins`
- `private_student_responses`
- `private_student_insights`
- `private_student_progress`

---

## What These Tables Do

### private_student_checkins
Represents a "session" where a student answers questions about their placement anxiety.
- Tracks when the check-in started (`created_at`)
- Records when it was finished (`completed_at`)
- Stores which organization the student belongs to (for data isolation)

### private_student_responses
Individual answers to the 8 questions in the Know Me flow.
- Supports multiple-choice (many IDs selected)
- Supports free-text responses
- Stored as JSON for flexibility

### private_student_insights
AI-generated analysis from OpenAI based on student responses.
- Generates a personalized "headline" insight
- Lists "blockers" (what's holding them back)
- Provides "action_plan" (concrete MentorMuni actions)
- Falls back to heuristic if OpenAI fails

### private_student_progress
Growth metrics over 30–45 days.
- Compares first check-in to latest check-in
- Tracks confidence, clarity, communication, etc.
- Powers the "See how far you've come" visualization

---

## Data Privacy & Security

✅ **Student-only access**: Only the authenticated student can view their Know Me data
✅ **No TPO/HOD visibility**: These tables are never queried by org dashboards
✅ **Strict foreign keys**: All responses linked to a specific student & check-in
✅ **On-delete cascade**: Deleting a student cascades to all their private data
✅ **No org joins**: API code explicitly prevents cross-joins with org tables

---

## Timeline

| Component | Status | Date |
|-----------|--------|------|
| Backend code | ✅ Done | Aug 10, 2026 |
| Database models | ✅ Done | Aug 10, 2026 |
| API endpoints | ✅ Done | Aug 10, 2026 |
| Frontend UI | ✅ Done | Aug 10, 2026 |
| **PostgreSQL migration** | ⏳ **PENDING** | **NOW** |

---

## Next Action

**Provide your PostgreSQL connection URL**, then run:

```bash
cd /Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api
export DATABASE_URL="your_postgresql_url_here"
../.venv/bin/alembic upgrade head
```

Example:
```bash
export DATABASE_URL="postgresql+asyncpg://rahul:password@localhost:5432/mentormuni"
../.venv/bin/alembic upgrade head
```

Once complete, you'll be able to:
1. Start the API
2. Test Know Me endpoints  
3. Use the feature end-to-end
4. See OpenAI insights generated in real-time
