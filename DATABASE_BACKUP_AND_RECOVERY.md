# MentorMuni Database - Backup & Recovery Guide

## Overview

This guide provides complete documentation for backing up, restoring, and migrating the MentorMuni database, including all Know Me private tables.

---

## 1. Alembic Migrations - Complete List

All database migrations are in: `/mentormuni-api/alembic/versions/`

### Migration Files (in order)
```
0001_phase1_core_tables.py              ← Users, Organizations, Roles, etc.
0002_platform_portal.py                 ← Platform auth & features
0003_org_portal_rbac.py                 ← TPO/HOD access control
0004_org_ops_notifications.py            ← Notifications system
0005_student_enrollment.py               ← Student enrollment tracking
0006_plat_must_chg_pwd.py                ← Password change enforcement
0007_subscription_plan_codes.py           ← Subscription plans
0008_user_must_change_password.py         ← User password management
0009_org_admin_title.py                  ← Org admin titles
0010_campus_notifications.py              ← Campus-wide notifications
0011_workspace_items.py                  ← Workspace features
0012_upcoming_drives.py                  ← Drive scheduling
0013_student_roadmap.py                  ← Student roadmap & skills
0014_progress_topics.py                  ← Progress tracking
0015_dept_admin_title.py                 ← Department admin titles
0016_company_intelligence.py              ← Company intelligence data
0017_coding_assessment.py                ← Coding assessment system
0018_coding_attempt_active_uniq.py        ← Coding attempt constraints
0019_coding_question_bank.py              ← Coding question bank
0020_private_student_checkins.py          ← KNOW ME FEATURE (NEW)
```

### Know Me Feature Tables (0020)
```
private_student_checkins     ← Check-in sessions
private_student_responses    ← Student responses to questions
private_student_insights     ← AI-generated insights
private_student_progress     ← Progress metrics
```

---

## 2. Database Backup Strategies

### Option A: Full PostgreSQL Backup (Recommended)

**Backup to file:**
```bash
# Backup entire database
pg_dump -h crossover.proxy.rlwy.net -U postgres -d railway > mentormuni_backup_$(date +%Y%m%d_%H%M%S).sql

# Or with compressed output
pg_dump -h crossover.proxy.rlwy.net -U postgres -d railway | gzip > mentormuni_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# With password (will prompt)
PGPASSWORD="SpatqMOLKPHvtFrWrBvmrGYZHrzatGCG" pg_dump -h crossover.proxy.rlwy.net -U postgres -d railway > backup.sql
```

**Backup only private tables:**
```bash
# Know Me tables only
pg_dump -h crossover.proxy.rlwy.net -U postgres -d railway \
  -t private_student_checkins \
  -t private_student_responses \
  -t private_student_insights \
  -t private_student_progress > know_me_backup_$(date +%Y%m%d).sql
```

### Option B: Using Alembic (Recommended for migrations)

**Generate SQL from migration files:**
```bash
cd mentormuni-api

# See current database version
alembic current

# See all available migrations
alembic history

# Generate SQL without applying (dry-run)
alembic upgrade --sql <revision> > migration.sql
```

### Option C: Scheduled Automated Backups

**Create a backup script** (`backup-db.sh`):
```bash
#!/bin/bash

BACKUP_DIR="/backups/mentormuni"
DB_HOST="crossover.proxy.rlwy.net"
DB_USER="postgres"
DB_NAME="railway"
DB_PASS="SpatqMOLKPHvtFrWrBvmrGYZHrzatGCG"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Full backup
PGPASSWORD="$DB_PASS" pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | \
  gzip > "$BACKUP_DIR/full_backup_$TIMESTAMP.sql.gz"

# Know Me tables backup
PGPASSWORD="$DB_PASS" pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME \
  -t private_student_checkins \
  -t private_student_responses \
  -t private_student_insights \
  -t private_student_progress | \
  gzip > "$BACKUP_DIR/know_me_backup_$TIMESTAMP.sql.gz"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

**Schedule with cron:**
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup-db.sh >> /var/log/db_backup.log 2>&1
```

---

## 3. Database Restore Procedures

### Restore from Full Backup

```bash
# Restore to same database
psql -h crossover.proxy.rlwy.net -U postgres -d railway < backup.sql

# Restore compressed backup
gunzip -c backup.sql.gz | psql -h crossover.proxy.rlwy.net -U postgres -d railway

# With password prompt
PGPASSWORD="password" psql -h crossover.proxy.rlwy.net -U postgres -d railway < backup.sql
```

### Restore Only Know Me Tables

```bash
# Restore just Know Me data
psql -h crossover.proxy.rlwy.net -U postgres -d railway < know_me_backup.sql
```

### Restore to New Database

```bash
# Create new database
createdb -h crossover.proxy.rlwy.net -U postgres mentormuni_restored

# Restore backup into new database
pg_dump -h crossover.proxy.rlwy.net -U postgres -d railway | \
  psql -h crossover.proxy.rlwy.net -U postgres -d mentormuni_restored
```

---

## 4. Migration to New Database

### Step 1: Prepare New Database

```bash
# Create new database
createdb -h new-host -U postgres -d mentormuni_new

# Or if using Railway, create new PostgreSQL plugin through UI
```

### Step 2: Run All Migrations

```bash
cd mentormuni-api

# Set new database URL
export DATABASE_URL="postgresql+asyncpg://postgres:password@new-host:5432/mentormuni_new"

# Run all migrations
alembic upgrade head

# Verify
alembic current  # Should show: 0020_private_student_checkins
```

### Step 3: Verify Tables

```bash
# Connect to new database
psql -h new-host -U postgres -d mentormuni_new

# List all tables
\dt

# Verify private tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'private_%';
```

### Step 4: Restore Data (Optional)

If you have existing data to migrate:

```bash
# Dump only data from old database
pg_dump -h old-host -U postgres -d railway --data-only > data.sql

# Restore to new database
psql -h new-host -U postgres -d mentormuni_new < data.sql
```

---

## 5. Schema Documentation

### Know Me Private Tables Schema

#### Table: `private_student_checkins`
```sql
CREATE TABLE private_student_checkins (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL
);
CREATE INDEX ix_psc_student_id_created ON private_student_checkins(student_id, created_at);
```

#### Table: `private_student_responses`
```sql
CREATE TABLE private_student_responses (
    id SERIAL PRIMARY KEY,
    checkin_id INTEGER NOT NULL REFERENCES private_student_checkins(id) ON DELETE CASCADE,
    question_key VARCHAR(128) NOT NULL,
    response_type VARCHAR(32) NOT NULL,  -- 'multiple_choice' | 'free_text'
    response_value JSONB NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_psr_checkin_id ON private_student_responses(checkin_id);
```

#### Table: `private_student_insights`
```sql
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
```

#### Table: `private_student_progress`
```sql
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

## 6. Disaster Recovery Checklist

- [ ] **Weekly Backups**: Automated full backups stored securely
- [ ] **Monthly Test Restore**: Test restoring backup to verify integrity
- [ ] **Documentation**: Keep migration files in version control
- [ ] **Access Credentials**: Store database passwords in secure vault (not in git)
- [ ] **Monitoring**: Set up alerts for database errors
- [ ] **Point-in-Time Recovery**: Maintain transaction logs if using PostgreSQL WAL

### Backup Checklist Before Production

- [ ] Full database backup created
- [ ] Know Me tables backup created
- [ ] Backup tested by restoring to test database
- [ ] All migration files are in git
- [ ] Database credentials are in .env (not in git)
- [ ] Backup location documented
- [ ] Restore procedure tested
- [ ] Team trained on recovery process

---

## 7. Common Recovery Scenarios

### Scenario A: Corrupt Know Me Table

**Restore only Know Me data:**
```bash
# Backup current state first
pg_dump -h host -U postgres -d railway \
  -t private_student_insights > backup_before_restore.sql

# Restore from known good backup
psql -h host -U postgres -d railway < know_me_backup_clean.sql
```

### Scenario B: Accidental Data Deletion

**Restore from point-in-time backup:**
```bash
# If using PostgreSQL WAL (Write-Ahead Logging):
pg_restore -h host -U postgres -d railway \
  --target-time "2026-08-10 12:00:00" backup.tar
```

### Scenario C: Migration to Different Host

```bash
# 1. Backup from old host
pg_dump -h old-host -U postgres -d railway > full_backup.sql

# 2. Create new database on new host
createdb -h new-host -U postgres -d railway

# 3. Restore to new host
psql -h new-host -U postgres -d railway < full_backup.sql

# 4. Verify
psql -h new-host -U postgres -d railway -c "SELECT COUNT(*) FROM users;"
```

---

## 8. Files to Keep in Version Control

```
✓ mentormuni-api/alembic/versions/*.py     (All migration files)
✓ mentormuni-api/alembic/env.py            (Alembic config)
✓ mentormuni-api/alembic/alembic.ini       (Alembic settings)
✓ DATABASE_BACKUP_AND_RECOVERY.md          (This file)
✓ .env.example                             (Example env vars - NO secrets)

✗ .env                                      (Never commit this!)
✗ backup files (*.sql, *.sql.gz)            (Store in secure backup location)
✗ PostgreSQL password                       (Use environment variables)
```

---

## 9. Database Size & Performance

### Check Database Size
```bash
psql -h crossover.proxy.rlwy.net -U postgres -d railway -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Optimize Private Tables (After large deletions)
```bash
-- Reclaim disk space from private tables
VACUUM ANALYZE private_student_checkins;
VACUUM ANALYZE private_student_responses;
VACUUM ANALYZE private_student_insights;
VACUUM ANALYZE private_student_progress;
```

---

## 10. Monitoring & Alerts

### Key Metrics to Monitor

- **Backup success**: Daily automated backup completion
- **Database size**: Alerts if growing unexpectedly
- **Replication lag**: If using read replicas
- **Connection count**: Alerts for connection pools exhaustion
- **Slow queries**: Monitor slow query log
- **Know Me table growth**: Alert if responses grow unexpectedly

### Sample Monitoring Query

```sql
-- Check private table sizes
SELECT 
  tablename,
  COUNT(*) as row_count,
  pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size
FROM (
  SELECT 'private_student_checkins' as tablename
  UNION ALL
  SELECT 'private_student_responses'
  UNION ALL
  SELECT 'private_student_insights'
  UNION ALL
  SELECT 'private_student_progress'
) t
GROUP BY tablename;
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Full Backup | `pg_dump -h host -U postgres -d railway > backup.sql` |
| Full Restore | `psql -h host -U postgres -d railway < backup.sql` |
| Know Me Backup | `pg_dump -h host -U postgres -d railway -t private_* > km_backup.sql` |
| Current Migration | `cd mentormuni-api && alembic current` |
| Apply All Migrations | `cd mentormuni-api && alembic upgrade head` |
| List Tables | `psql -h host -U postgres -d railway -c "\dt"` |
| DB Size | `psql -h host -U postgres -d railway -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database;"` |

---

## Support Resources

- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **PostgreSQL Backup**: https://www.postgresql.org/docs/current/backup.html
- **pg_dump Manual**: https://www.postgresql.org/docs/current/app-pgdump.html
- **Railway PostgreSQL**: https://docs.railway.app/databases/postgresql

---

**Last Updated**: August 10, 2026  
**Know Me Feature Version**: 1.0 (0020_private_student_checkins)  
**Database Host**: Railway (crossover.proxy.rlwy.net:52225)
