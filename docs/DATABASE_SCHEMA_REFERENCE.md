# MentorMuni Database - Complete Schema Reference

## Overview

This document serves as a complete reference for all database tables, columns, relationships, and indexes in the MentorMuni platform, with special focus on the Know Me feature's private tables.

---

## Core Tables (Phase 1 - 0001)

### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    department_id INTEGER REFERENCES departments(id),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR UNIQUE NOT NULL,
    mobile VARCHAR,
    username VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'ACTIVE',
    -- Additional fields...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);
```

### organizations
```sql
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    code VARCHAR UNIQUE,
    status VARCHAR DEFAULT 'ACTIVE',
    -- Company details...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### roles
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_code VARCHAR UNIQUE NOT NULL,  -- 'STUDENT', 'TPO', 'HOD', etc.
    role_name VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### departments
```sql
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Know Me Private Tables (Phase 3 - 0020)

### private_student_checkins
**Purpose**: Track individual Know Me check-in sessions

```sql
CREATE TABLE private_student_checkins (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    status VARCHAR DEFAULT 'in_progress',  -- 'in_progress', 'completed'
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL  -- When check-in was finished
);
CREATE INDEX ix_psc_student_id_created ON private_student_checkins(student_id, created_at);
```

**Sample Queries**:
```sql
-- Get all check-ins for a student
SELECT * FROM private_student_checkins 
WHERE student_id = 123 
ORDER BY created_at DESC;

-- Get latest completed check-in
SELECT * FROM private_student_checkins 
WHERE student_id = 123 AND completed_at IS NOT NULL
ORDER BY completed_at DESC LIMIT 1;

-- Count check-ins per student
SELECT student_id, COUNT(*) as checkin_count
FROM private_student_checkins
GROUP BY student_id;
```

---

### private_student_responses
**Purpose**: Store individual responses to Know Me questions

```sql
CREATE TABLE private_student_responses (
    id SERIAL PRIMARY KEY,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    question_key VARCHAR(128) NOT NULL,  -- e.g., 'placement_pressure', 'technical_confidence'
    response_type VARCHAR(32) NOT NULL,  -- 'multiple_choice' | 'free_text'
    response_value JSONB NULL,           -- { "selected_ids": [...], "free_text": "..." }
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_psr_checkin_id ON private_student_responses(checkin_id);
CREATE INDEX ix_psr_question_key ON private_student_responses(question_key);
```

**Response Value Structure**:
```json
{
  "selected_ids": ["id1", "id2", "id3"],
  "free_text": "Additional context from student..."
}
```

**Sample Queries**:
```sql
-- Get all responses for a check-in
SELECT * FROM private_student_responses 
WHERE checkin_id = 1 
ORDER BY created_at;

-- Get responses for specific question
SELECT pr.* 
FROM private_student_responses pr
JOIN private_student_checkins psc ON pr.checkin_id = psc.id
WHERE psc.student_id = 123 AND pr.question_key = 'placement_pressure';

-- Count students who answered a question
SELECT COUNT(DISTINCT checkin_id) 
FROM private_student_responses 
WHERE question_key = 'technical_confidence';
```

---

### private_student_insights
**Purpose**: Store AI-generated insights from OpenAI

```sql
CREATE TABLE private_student_insights (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    source VARCHAR(32) NOT NULL DEFAULT 'openai',  -- 'openai' | 'heuristic'
    model VARCHAR(64) NULL,  -- 'gpt-4.1' | 'gpt-4-turbo' etc.
    headline TEXT NOT NULL,  -- Main insight summary
    what_i_hear JSONB NOT NULL DEFAULT '[]'::jsonb,  -- List of interpretations
    narrative TEXT NULL,      -- Full narrative from AI (optional)
    blockers JSONB NOT NULL DEFAULT '[]'::jsonb,     -- Blocker analysis
    action_plan JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Recommended actions
    full_insight_json JSONB NOT NULL DEFAULT '{}'::jsonb,  -- Complete response
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_psi_student_id_created ON private_student_insights(student_id, created_at);
```

**JSON Structure Examples**:

```json
{
  "what_i_hear": [
    "You care deeply about placement",
    "The uncertainty is draining you",
    "You need a clear next step"
  ],
  "blockers": [
    {
      "order": 1,
      "title": "Unclear starting point",
      "student_quote": "I don't know where to start",
      "mentormuni_action": "Take Skill Readiness Test"
    },
    {
      "order": 2,
      "title": "Technical gaps",
      "student_quote": "I'm not sure about DSA",
      "mentormuni_action": "Complete 2-week DSA focus"
    }
  ],
  "action_plan": [
    {
      "priority": 1,
      "action_type": "Assessment",
      "description": "Take Skill Readiness Test",
      "tool_code": "skill_readiness",
      "duration_minutes": 30
    },
    {
      "priority": 2,
      "action_type": "Practice",
      "description": "Record 60-second intro",
      "tool_code": null,
      "duration_minutes": 10
    }
  ]
}
```

**Sample Queries**:
```sql
-- Get latest insight for a student
SELECT * FROM private_student_insights 
WHERE student_id = 123 
ORDER BY created_at DESC LIMIT 1;

-- Get insights generated by OpenAI (not heuristic)
SELECT * FROM private_student_insights 
WHERE source = 'openai' AND student_id = 123;

-- Count insights per source
SELECT source, COUNT(*) as count 
FROM private_student_insights 
GROUP BY source;

-- Extract blocker titles
SELECT 
    student_id,
    jsonb_array_elements(blockers)->>'title' as blocker_title
FROM private_student_insights
WHERE student_id = 123;
```

---

### private_student_progress
**Purpose**: Track student progress over time (30-45 day comparisons)

```sql
CREATE TABLE private_student_progress (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    metric_key VARCHAR(64) NOT NULL,  -- 'confidence', 'clarity', 'communication', etc.
    value_before INTEGER NULL,  -- Score before (0-100)
    value_after INTEGER NULL,   -- Score after (0-100)
    unit VARCHAR(32) DEFAULT 'percent',  -- 'percent', 'score', 'count'
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_psp_student_id_created ON private_student_progress(student_id, recorded_at);
```

**Sample Data**:
```sql
-- First check-in baseline
INSERT INTO private_student_progress VALUES (
    NULL, 20, 1, 'placement_confidence', NULL, 45, 'percent', NOW()
);

-- Follow-up check-in after 45 days
INSERT INTO private_student_progress VALUES (
    NULL, 20, 2, 'placement_confidence', 45, 72, 'percent', NOW()
);
```

**Sample Queries**:
```sql
-- Get progress for a student
SELECT 
    metric_key,
    value_before,
    value_after,
    (value_after - value_before) as improvement
FROM private_student_progress 
WHERE student_id = 123
ORDER BY recorded_at DESC;

-- Calculate average improvement
SELECT 
    metric_key,
    AVG(value_after - value_before) as avg_improvement
FROM private_student_progress 
WHERE value_before IS NOT NULL AND value_after IS NOT NULL
GROUP BY metric_key;

-- Students with positive progress
SELECT DISTINCT student_id
FROM private_student_progress
WHERE value_after > value_before
ORDER BY recorded_at DESC;
```

---

## Relationships & Data Flow

### Know Me Data Flow

```
User (STUDENT role)
    ↓
private_student_checkins
    ├── private_student_responses (1:many)
    │   └── [8 responses per check-in]
    ├── private_student_insights (1:1)
    │   └── [AI-generated insight]
    └── private_student_progress (1:many)
        └── [Progress metrics over time]
```

### Foreign Key Relationships

```sql
-- All private tables reference users
ALTER TABLE private_student_checkins 
    ADD CONSTRAINT fk_psc_student 
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- All private tables reference organizations for multi-tenancy
ALTER TABLE private_student_checkins 
    ADD CONSTRAINT fk_psc_org 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Responses linked to check-ins
ALTER TABLE private_student_responses 
    ADD CONSTRAINT fk_psr_checkin 
    FOREIGN KEY (checkin_id) REFERENCES private_student_checkins(id) ON DELETE CASCADE;

-- Insights linked to check-ins
ALTER TABLE private_student_insights 
    ADD CONSTRAINT fk_psi_checkin 
    FOREIGN KEY (checkin_id) REFERENCES private_student_checkins(id) ON DELETE CASCADE;

-- Progress linked to check-ins
ALTER TABLE private_student_progress 
    ADD CONSTRAINT fk_psp_checkin 
    FOREIGN KEY (checkin_id) REFERENCES private_student_checkins(id) ON DELETE CASCADE;
```

---

## Data Isolation Strategy

### Privacy Enforcement (No Cross-Joins)

```sql
-- ✗ NEVER do this - violates privacy
SELECT * FROM private_student_checkins psc
JOIN organizations o ON psc.organization_id = o.id  -- Exposes to org dashboards
WHERE o.id = 1;

-- ✗ NEVER do this - exposes to TPO/HOD
SELECT psc.* FROM private_student_checkins psc
JOIN users u ON psc.student_id = u.id
JOIN student_roadmap sr ON u.id = sr.student_id  -- Mixes private + org data
WHERE u.organization_id = 1;

-- ✓ CORRECT - Student-only access
SELECT * FROM private_student_checkins 
WHERE student_id = $1;  -- Only queried by authenticated student
```

### Authorization Pattern

```python
# Backend enforces at API layer
@router.post("/student/know-me/start")
async def start_checkin(
    user: User = Depends(require_roles(STUDENT)),  # Only STUDENT role allowed
    db: AsyncSession = Depends(get_db)
):
    # Queries only include WHERE student_id = user.id
    checkins = db.query(PrivateStudentCheckIn).filter(
        PrivateStudentCheckIn.student_id == user.id
    ).all()
    
    # Never join with org tables or make visible to org portal
```

---

## Indexes for Performance

### Primary Indexes (Created with tables)
```sql
-- Check-in lookup by student (most common query)
ix_psc_student_id_created(student_id, created_at)

-- Response lookup within check-in
ix_psr_checkin_id(checkin_id)

-- Insight lookup by student (progress tracking)
ix_psi_student_id_created(student_id, created_at)

-- Progress lookup by student (analytics)
ix_psp_student_id_created(student_id, recorded_at)
```

### Optional Indexes (for scale)
```sql
-- If querying by question_key frequently
CREATE INDEX ix_psr_question_key ON private_student_responses(question_key);

-- If analytics on response distribution
CREATE INDEX ix_psr_question_response ON private_student_responses(question_key, response_type);

-- If checking progress by metric
CREATE INDEX ix_psp_metric_key ON private_student_progress(metric_key, recorded_at);
```

---

## Backup & Restore Reference

### Backup Private Tables Only
```bash
pg_dump -h host -U postgres -d railway \
  -t private_student_checkins \
  -t private_student_responses \
  -t private_student_insights \
  -t private_student_progress \
  > know_me_backup.sql
```

### Export Schema
```bash
pg_dump -h host -U postgres -d railway \
  --schema-only \
  > schema_only.sql
```

### Restore Specific Table
```bash
psql -h host -U postgres -d railway < know_me_backup.sql
```

---

## Statistics & Monitoring

### Table Sizes
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'private_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Row Counts
```sql
SELECT 
    'private_student_checkins' as table_name,
    COUNT(*) as row_count
FROM private_student_checkins
UNION ALL
SELECT 'private_student_responses', COUNT(*) FROM private_student_responses
UNION ALL
SELECT 'private_student_insights', COUNT(*) FROM private_student_insights
UNION ALL
SELECT 'private_student_progress', COUNT(*) FROM private_student_progress;
```

### Index Usage
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename LIKE 'private_%'
ORDER BY idx_scan DESC;
```

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor backup completion
- Check for connection spikes
- Monitor slow query log

**Weekly**:
- ANALYZE tables for statistics
- Check index usage
- Verify replication lag (if using replicas)

**Monthly**:
- VACUUM ANALYZE private tables
- Purge old audit logs (if logging enabled)
- Review and archive large responses

**Quarterly**:
- Test restore procedure
- Update statistics
- Review index performance

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-08-10 | Initial Know Me feature (0020_private_student_checkins) |

---

**Last Updated**: August 10, 2026  
**Scope**: All 20 migrations (0001 - 0020)  
**Focus**: Know Me Private Tables Architecture
