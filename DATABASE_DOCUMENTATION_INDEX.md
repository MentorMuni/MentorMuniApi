# MentorMuni Database - Documentation Index

## Complete Database & Backup Documentation

All database-related documentation, migration scripts, and recovery guides are now available. Use this index to find what you need.

---

## 📋 Documentation Files

### 1. **DATABASE_BACKUP_AND_RECOVERY.md** (Primary Guide)
**Location**: `/MentorMuniAPI/DATABASE_BACKUP_AND_RECOVERY.md`

**Contents**:
- Complete Alembic migration list (0001 - 0020)
- Backup strategies (full, partial, automated)
- Restore procedures (from backup, point-in-time, different host)
- Migration to new database
- Schema documentation for all Know Me tables
- Disaster recovery checklist
- Common recovery scenarios
- Database monitoring setup

**Use When**:
- Setting up automated backups
- Restoring from backup
- Migrating to new database
- Database failure recovery
- Creating backup schedule

---

### 2. **docs/DATABASE_SCHEMA_REFERENCE.md** (Technical Reference)
**Location**: `/MentorMuniAPI/docs/DATABASE_SCHEMA_REFERENCE.md`

**Contents**:
- Complete schema for all tables
- Know Me private table definitions
- Column details & relationships
- Sample SQL queries
- JSON structure examples
- Data isolation strategy
- Index definitions
- Performance monitoring queries
- Maintenance procedures

**Use When**:
- Understanding table structure
- Writing SQL queries
- Optimizing database performance
- Understanding relationships
- Data isolation verification

---

### 3. **MIGRATION_INSTRUCTIONS.md** (Setup Guide)
**Location**: `/MentorMuniAPI/MIGRATION_INSTRUCTIONS.md`

**Contents**:
- Step-by-step migration guide
- Configuration after migration
- Testing the API
- Troubleshooting common issues
- Migration file reference

**Use When**:
- Setting up new database
- Troubleshooting migrations
- Testing endpoints

---

### 4. **KNOW_ME_STATUS.md** (Feature Status)
**Location**: `/MentorMuniAPI/KNOW_ME_STATUS.md`

**Contents**:
- Feature completion status
- Database verification
- How to run locally
- Testing endpoints
- API documentation
- Troubleshooting

**Use When**:
- Checking feature status
- Testing Know Me feature
- Understanding API endpoints

---

## 🛠️ Scripts

### **scripts/export-database-schema.sh** (Backup Utility)
**Location**: `/MentorMuniAPI/scripts/export-database-schema.sh`

**Features**:
- Full backup (schema + data)
- Schema-only export
- Data-only export
- Know Me tables only
- Automatic compression
- Auto-cleanup old backups (7 days)

**Usage**:
```bash
# Full backup
./scripts/export-database-schema.sh --full --compressed

# Know Me backup only
./scripts/export-database-schema.sh --know-me-only

# Schema only
./scripts/export-database-schema.sh --schema-only

# Custom output
./scripts/export-database-schema.sh --full --output /path/to/backup.sql.gz
```

---

## 📂 Alembic Migrations

**Location**: `/mentormuni-api/alembic/versions/`

**All Migration Files** (in order):
```
0001_phase1_core_tables.py              ← Core tables (users, orgs, roles)
0002_platform_portal.py                 ← Platform authentication
0003_org_portal_rbac.py                 ← Access control
0004_org_ops_notifications.py            ← Notifications
0005_student_enrollment.py               ← Enrollment
0006_plat_must_chg_pwd.py                ← Password enforcement
0007_subscription_plan_codes.py           ← Plans
0008_user_must_change_password.py         ← Password management
0009_org_admin_title.py                  ← Admin titles
0010_campus_notifications.py              ← Campus notifications
0011_workspace_items.py                  ← Workspace
0012_upcoming_drives.py                  ← Drives
0013_student_roadmap.py                  ← Roadmap
0014_progress_topics.py                  ← Progress
0015_dept_admin_title.py                 ← Dept titles
0016_company_intelligence.py              ← Company data
0017_coding_assessment.py                ← Coding
0018_coding_attempt_active_uniq.py        ← Coding constraints
0019_coding_question_bank.py              ← Question bank
0020_private_student_checkins.py          ← KNOW ME FEATURE ⭐
```

---

## 🚀 Quick Start

### Backup Database
```bash
# Export backup script
./scripts/export-database-schema.sh --full --compressed

# Output: ./backups/full_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Restore Database
```bash
# Restore from compressed backup
gunzip -c backup.sql.gz | psql -h host -U postgres -d railway

# Or use the script
psql -h host -U postgres -d railway < backup.sql
```

### Run Migrations
```bash
cd mentormuni-api
alembic upgrade head
```

### Verify Migration
```bash
alembic current  # Should show: 0020_private_student_checkins
```

---

## 📊 Database Statistics

### Quick Check
```bash
# Check table sizes
psql -h host -U postgres -d railway -c "
  SELECT tablename, pg_size_pretty(pg_total_relation_size('public.'||tablename))
  FROM pg_tables
  WHERE schemaname = 'public' AND tablename LIKE 'private_%';"
```

### Know Me Tables Size
```sql
SELECT 
    'private_student_checkins' as table_name,
    COUNT(*) as rows
FROM private_student_checkins
UNION ALL
SELECT 'private_student_responses', COUNT(*) FROM private_student_responses
UNION ALL
SELECT 'private_student_insights', COUNT(*) FROM private_student_insights
UNION ALL
SELECT 'private_student_progress', COUNT(*) FROM private_student_progress;
```

---

## 🔒 Data Privacy & Security

### Privacy Guarantees
✅ **Student-only access**: Private tables only accessible to STUDENT role  
✅ **No TPO/HOD visibility**: Tables never joined with org dashboards  
✅ **Data isolation**: Strict foreign keys, on-delete cascade  
✅ **Authorization enforced**: Backend layer, not just UI  

### Backup Security
✅ Store backups in secure location (not in git)  
✅ Use encryption for remote backups  
✅ Test restore procedures monthly  
✅ Document backup location & access procedures  

---

## 🔧 Common Tasks

| Task | Command |
|------|---------|
| Full Database Backup | `./scripts/export-database-schema.sh --full --compressed` |
| Know Me Backup | `./scripts/export-database-schema.sh --know-me-only` |
| Restore from Backup | `psql -h host -U postgres -d railway < backup.sql` |
| Check Current Migration | `cd mentormuni-api && alembic current` |
| Apply All Migrations | `cd mentormuni-api && alembic upgrade head` |
| List All Migrations | `cd mentormuni-api && alembic history` |
| Check Private Tables | `psql -h host -U postgres -d railway -c "\dt private_*"` |
| Export Schema Only | `./scripts/export-database-schema.sh --schema-only` |

---

## 🆘 Troubleshooting

### Cannot connect to database
→ Check DATABASE_URL in `.env`  
→ Verify PostgreSQL is running  
→ Check credentials  

### Migration fails with "table already exists"
→ Run `alembic current` to check current state  
→ If already on 0020, migrations are complete  

### Know Me tables missing
→ Run `alembic upgrade head`  
→ Verify with `\dt private_*`  

### Backup file too large
→ Use `--know-me-only` for just Know Me data  
→ Use `--schema-only` for schema without data  

**See DATABASE_BACKUP_AND_RECOVERY.md for detailed troubleshooting**

---

## 📞 Support

### Documentation Links
- **Alembic**: https://alembic.sqlalchemy.org/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **pg_dump**: https://www.postgresql.org/docs/current/app-pgdump.html
- **Railway**: https://docs.railway.app/databases/postgresql

### Key Contacts
- Database Administrator: Check your team
- Railway Support: https://railway.app/support
- PostgreSQL Help: https://www.postgresql.org/community/

---

## 📅 Maintenance Schedule

**Daily**:
- Monitor backup completion
- Check database size growth

**Weekly**:
- Test query performance
- Review slow query log

**Monthly**:
- Test restore procedure
- Update index statistics
- VACUUM ANALYZE tables

**Quarterly**:
- Review backup retention
- Archive old data
- Update documentation

---

## ✅ Deployment Checklist

Before deploying to production:

- [ ] Automated backup script configured
- [ ] Backup location documented
- [ ] Restore procedure tested
- [ ] Database password in secure vault (not git)
- [ ] All migrations verified (`alembic current` → 0020)
- [ ] Private tables created and indexed
- [ ] Monitoring & alerts configured
- [ ] Data isolation verified
- [ ] Team trained on recovery
- [ ] Disaster recovery plan documented

---

## 📝 Last Updated

**Date**: August 10, 2026  
**Know Me Feature**: Version 1.0 (Migration 0020)  
**Database Host**: Railway (crossover.proxy.rlwy.net:52225)  
**Status**: ✅ Production Ready

---

**All documentation complete and ready for production use!** 🚀
