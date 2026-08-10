# Know Me Feature - Implementation & Migration Guide

## Summary

The "Know Me" feature is a **private, student-only experience** for self-reflection and placement anxiety management. This document covers the architecture, database schema, and migration steps required to deploy this feature.

---

## 1. Architecture Overview

### Data Isolation
- **Private tables**: `private_student_checkins`, `private_student_responses`, `private_student_insights`, `private_student_progress`
- **Never org-visible**: No TPO/HOD access, not joined with org dashboards
- **Backend enforcement**: `STUDENT` role only (403 Forbidden for others)
- **No persistence to org**: All insights are device-local or student-private

### Components

#### Backend (FastAPI)
- **Router**: `/student/know-me/*` endpoints (student-only)
- **Service**: Multi-step check-in, OpenAI insight generation, progress tracking
- **Database Models**: 4 private tables with strict foreign keys
- **Auth**: `require_roles(STUDENT)` on all endpoints

#### Frontend (React)
- **Page**: `/studentportal/know-me`
- **Navigation**: Sidebar with lock icon (🔒 Know Me)
- **State**: Device-local `localStorage` for session persistence
- **Flow**: Landing → Multi-step form → AI insight → Progress view

#### AI Integration
- **Model**: `gpt-4.1` (or `KNOW_MY_FEAR_MODEL` env var)
- **Prompt**: "Elder brother" conversational tone, reframes fears as actionable steps
- **Fallback**: Heuristic-based insights if OpenAI fails
- **Tokens**: Strict 1600-token limit per insight

---

## 2. Database Schema

### Tables

#### `private_student_checkins`
```sql
CREATE TABLE private_student_checkins (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL
);
INDEX: (student_id, created_at)
```

#### `private_student_responses`
```sql
CREATE TABLE private_student_responses (
    id INTEGER PRIMARY KEY,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    question_key VARCHAR(128) NOT NULL,
    response_type VARCHAR(32) NOT NULL,  -- 'multiple_choice' | 'free_text'
    response_value JSON NULL,             -- {"selected_ids": [...], "free_text": "..."}
    created_at TIMESTAMP NOT NULL
);
INDEX: (checkin_id)
```

#### `private_student_insights`
```sql
CREATE TABLE private_student_insights (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    source VARCHAR(32) NOT NULL DEFAULT 'openai',  -- 'openai' | 'heuristic'
    model VARCHAR(64) NULL,                         -- e.g., 'gpt-4.1'
    headline TEXT NOT NULL,
    what_i_hear JSON NOT NULL DEFAULT '[]',
    blockers JSON NOT NULL DEFAULT '[]',
    action_plan JSON NOT NULL DEFAULT '[]',
    full_insight_json JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL
);
INDEX: (student_id, created_at)
```

#### `private_student_progress`
```sql
CREATE TABLE private_student_progress (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    metric_key VARCHAR(64) NOT NULL,      -- 'confidence', 'clarity', etc.
    value_before INTEGER NULL,
    value_after INTEGER NULL,
    created_at TIMESTAMP NOT NULL
);
INDEX: (student_id, created_at)
```

---

## 3. Migration Steps

### Option A: Using Alembic (Recommended)

#### Step 1: Ensure PostgreSQL is configured
```bash
# Update .env with your PostgreSQL URL
# Example:
# DATABASE_URL=postgresql://user:password@localhost:5432/mentormuni
# Or Railway style:
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db
```

#### Step 2: Run migrations
```bash
cd /Users/rahul/Downloads/MentorMuni/MentorMuniAPI/mentormuni-api

# Run all pending migrations (up to 0020)
../.venv/bin/alembic upgrade head

# Or upgrade to a specific revision:
../.venv/bin/alembic upgrade 0020_private_student_checkins
```

#### Step 3: Verify tables exist
```bash
psql -U youruser -d mentormuni -c "\dt private_*"
```

### Option B: Manual SQL (if Alembic fails)

If you prefer to run the SQL directly, execute these commands in your PostgreSQL client:

```sql
-- 1. Create private_student_checkins
CREATE TABLE private_student_checkins (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL
);
CREATE INDEX ix_psc_student_id_created ON private_student_checkins(student_id, created_at);

-- 2. Create private_student_responses
CREATE TABLE private_student_responses (
    id SERIAL PRIMARY KEY,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    question_key VARCHAR(128) NOT NULL,
    response_type VARCHAR(32) NOT NULL,
    response_value JSONB NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_psr_checkin_id ON private_student_responses(checkin_id);

-- 3. Create private_student_insights
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

-- 4. Create private_student_progress
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

## 4. Verification Checklist

After running migrations, verify:

- [ ] All 4 private tables exist
- [ ] Foreign keys are correctly set to users & organizations
- [ ] Indexes are created for performance
- [ ] API can start: `uvicorn mentormuni-api.app.main:app --reload`
- [ ] Test endpoint returns 200: `POST /student/know-me/start`
- [ ] OpenAI API key is set in `.env` (`OPENAI_API_KEY`)
- [ ] Know Me model is configured (`KNOW_MY_FEAR_MODEL=gpt-4.1`)
- [ ] Frontend can access API at configured `VITE_API_URL`

---

## 5. API Endpoints

### POST `/student/know-me/start`
Starts a new check-in session.

**Response:**
```json
{
  "checkin_id": 1,
  "questions": [...],
  "total_steps": 8
}
```

### POST `/student/know-me/step/{checkin_id}`
Saves one step response.

**Body:**
```json
{
  "question_key": "placement_pressure",
  "response_type": "multiple_choice",
  "selected_ids": ["id1", "id2"],
  "free_text": "..."
}
```

### POST `/student/know-me/insight/{checkin_id}`
Generates AI insight after check-in completion.

**Response:**
```json
{
  "checkin_id": 1,
  "source": "openai",
  "headline": "You're caught between clarity and action",
  "what_i_hear": [...],
  "blockers": [...],
  "action_plan": [...]
}
```

### GET `/student/know-me/progress`
Compares first and latest check-ins for growth tracking (30–45 day follow-up).

**Response:**
```json
{
  "days_since_first": 45,
  "metrics": [...],
  "growth_summary": "You've grown over 45 days..."
}
```

---

## 6. Environment Variables

### Required
```bash
OPENAI_API_KEY=sk-...                          # OpenAI API key
DATABASE_URL=postgresql+asyncpg://...          # PostgreSQL connection
API_KEY=...                                    # Frontend API key
```

### Optional
```bash
KNOW_MY_FEAR_MODEL=gpt-4.1                     # AI model (default: gpt-4.1)
APP_ENV=development                            # Environment (development/production)
```

---

## 7. Troubleshooting

### Migration fails with "unknown function: now()"
- **Cause**: SQLite datetime syntax differs from PostgreSQL
- **Fix**: Ensure `DATABASE_URL` uses `postgresql+asyncpg://` not `sqlite://`

### API returns 500 on `/student/know-me/start`
- **Cause**: Private tables don't exist
- **Fix**: Run migrations with `alembic upgrade head`

### "Only students can use Know Me" (403)
- **Cause**: User role is not STUDENT
- **Fix**: Ensure Bearer token is for a student user, or use demo token `demo.student.*`

### OpenAI calls timing out
- **Cause**: Network issue or OpenAI API slow
- **Fix**: Increase `LLM_TIMEOUT_SECONDS` in `.env` (default: 120s)

---

## 8. Files Modified/Created

### Backend
- `app/models/private_checkin.py` - SQLAlchemy models
- `app/know_my_fear/router_v2.py` - API endpoints
- `app/know_my_fear/service_v2.py` - Business logic
- `app/know_my_fear/schemas_v2.py` - Pydantic schemas
- `app/know_my_fear/questions.py` - Question definitions
- `app/know_my_fear/insight_prompt.py` - AI system prompt
- `alembic/versions/0020_private_student_checkins.py` - Migration

### Frontend
- `src/studentPortal/pages/StudentKnowMePage.jsx` - React component
- `src/studentPortal/knowMe/knowMeApi.js` - API client
- `src/studentPortal/styles/know-me-v2.css` - Styles
- `src/studentPortal/components/home/StudentSidebar.jsx` - Navigation
- `src/studentPortal/StudentPortalApp.jsx` - Router config

---

## 9. Next Steps

1. **Update `.env`** with your PostgreSQL URL
2. **Run migrations**: `alembic upgrade head`
3. **Verify tables**: Check that 4 private tables exist
4. **Start API**: `uvicorn mentormuni-api.app.main:app --reload`
5. **Test frontend**: Navigate to `/studentportal/know-me`
6. **Monitor logs**: Watch for OpenAI API calls and database inserts

---

**Feature Status**: ✅ Implemented | ⏳ Awaiting PostgreSQL migration
