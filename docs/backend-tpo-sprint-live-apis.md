# Backend sprint brief: Live TPO portal (real data)

**Audience:** Backend team  
**Product:** MentorMuni Organization Portal (`/Organization/*`)  
**Sprint goal (this build):** Real data — **not** browser localStorage dummy.  
**In scope:** Students register + import · HOD invite **email** · notifications tables/API · audit_logs  
**Out of scope (next):** AI Campus Brief / OpenAI (`docs/backend-campus-insight-api.md` on frontend repo)

**Frontend source of truth (contracts + local fallback):**  
`Frontend/docs/backend-tpo-sprint-live-apis.md` · `departmentsApi.js` · `orgPortal/auth.js`

---

## 1. What “done” means for this sprint

A college TPO can run this **live** path on production-like env:

1. TPO logs in → lands on **dashboard** with **real** org/department/student counts (not frontend mock DB).  
2. TPO creates **departments** (CSE, ECE, …).  
3. TPO **invites HOD** (name + email) → backend creates HOD user + **sends email** with activate link.  
4. HOD opens `/activate-hod?token=…` → sets password → status **active**.  
5. HOD logs in at `/Organization/login` → reaches **home/dashboard** successfully.  
6. HOD can **change / reset password** (logged-in change-password; forgot-password already exists).  
7. TPO can **invite / import / register students** into departments; approve queue if you use invite→approve.  
8. Key actions write **audit_logs**; system can create **notifications** rows (in-app and/or email jobs).

If step 3–5 works end-to-end with real DB + email, the portal is “live” for the HOD handoff. Dummy `mm-org-tpo-db-v1` localStorage is only a frontend fallback until these APIs exist **on the paths the FE calls**.

---

## 2. Auth model (already used by frontend)

| Header / piece | Use |
|----------------|-----|
| `X-API-Key` | All org APIs |
| `Authorization: Bearer <org JWT>` | Logged-in TPO / HOD / Student |
| No JWT | Activate links, college list, login |

**Existing (keep / extend):**

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/auth/login` | Body: email\|username + password + optional `organization_code` |
| `GET` | `/auth/me` | Enrich session after login |
| `POST` | `/auth/change-password` | `{ current_password, new_password }` |
| `POST` | `/auth/forgot-password` | Already live |
| `POST` | `/auth/reset-password` | Already live |
| `POST` | `/platform/auth/activate-tpo` | TPO activate (already live) |
| `GET` | `/organizations/colleges` | Login college picker (API key) |

**Roles for this sprint:**

| FE role label | Backend `role_code` | Who | Portal access |
|---------------|---------------------|-----|----------------|
| `ORG_ADMIN` / `TPO` | `ORG_ADMIN` | Placement head | Full TPO modules |
| `HOD` / `DEPARTMENT_HEAD` | `DEPARTMENT_ADMIN` | Dept mentor | Dashboard home after activate |
| `STUDENT` | `STUDENT` | Enrolled student | Optional this sprint if register/import only creates accounts |

Login / `/auth/me` — FE reads (snake_case OK; FE normalizes):

```json
{
  "id": 1,
  "email": "hod.cse@college.edu",
  "first_name": "Priya",
  "last_name": "Sharma",
  "role": "DEPARTMENT_ADMIN",
  "organization_id": 10,
  "organization_code": "ABC",
  "department_id": 3,
  "permissions": ["VIEW_DEPARTMENT_STUDENTS", "..."]
}
```

FE also accepts `must_change_password` / `mustChangePassword` if present (optional).

---

## 3. Frontend contract map ↔ current backend (gap analysis)

This is the important part for this repo: **much of Track A already exists**, but under **different paths / shapes** than `departmentsApi.js` and Enrollment expect. Frontend falls back to localStorage on **404 / 501**.

### 3.1 Priority APIs — FE expected vs BE today

| P | FE expects | Backend today | Gap |
|---|------------|---------------|-----|
| 1 | `GET/POST/PUT/DELETE /organizations/departments` | `GET/POST/PUT/DELETE /departments` | **Path prefix.** Response missing `hod_*`, `student_count`. |
| 2 | `POST …/departments/:id/hod` (+ reinvite / revoke / replace) | `POST /users` with `role_code=DEPARTMENT_ADMIN` + email via `send_hod_invite_email` | **No nested HOD lifecycle routes.** No revoke/replace as first-class ops. |
| 3 | `POST /auth/activate-hod { token, new_password }` | `POST /auth/activate` (shared TPO/HOD) | **Alias missing.** FE tries `/auth/activate-hod` then `/platform/auth/activate-hod`. |
| 4 | login / me / change-password for HOD | ✅ `/auth/login`, `/auth/me`, `/auth/change-password`, forgot/reset | Soft gap: enrich `organization_name` on me if FE needs it. |
| 5 | Students invite / import / list (+ approve) | `POST /students/register`, `POST /users/import` (CSV), `GET /users?role_code=STUDENT`, `PUT /users/{id}/approve\|reject` | **No** `/organizations/students/*`. Enrollment UI still **100% local**. Import is CSV multipart, not JSON rows. |
| 6 | `GET /organizations/notifications` | `GET /notifications`, `/notifications/inbox`, mark-read | Path + inbox shape differ; email for HOD is **direct SendGrid-style send**, not notification outbox worker. |
| 7 | `GET /organizations/audit-logs` | Table `audit_logs` + `write_audit()` used on user/notif mutates | **No list API.** Dept CRUD not audited yet. |
| 8 | `GET /organizations/dashboard` | `GET /dashboard` (identity funnel counts) | Path + field names differ (`students_pending` vs `pending_invites`, etc.). |

### 3.2 What FE actually calls today (wired)

| Frontend file | Calls |
|---------------|--------|
| `orgPortal/auth.js` | `POST /auth/login`, `GET /auth/me`, `POST /auth/change-password`, `POST /platform/auth/activate-tpo`, `POST /auth/activate-hod` (fallback `/platform/auth/activate-hod`, then local) |
| `organizationPortal/departmentsApi.js` | CRUD + HOD invite/reinvite/revoke/replace under `/organizations/departments…`; local on 404/501 |
| `orgPortal/colleges.js` | `GET /organizations/colleges` |
| Enrollment / Programs / Drives | **local store only** until student APIs stabilize |

### 3.3 Department JSON FE expects

```json
{
  "id": 1,
  "name": "Computer Science",
  "code": "CSE",
  "hod_name": "Dr. Priya",
  "hod_email": "hod.cse@college.edu",
  "hod_status": "invited",
  "student_count": 0,
  "invited_at": "…",
  "activated_at": null
}
```

`hod_status`: `unassigned` | `invited` | `active` | `revoked`  
Today’s `DepartmentResponse`: `id, organization_id, name, code, status, created_at` only.

### 3.4 HOD invite FE expects

```http
POST /organizations/departments/{id}/hod
{ "name": "Dr. Priya", "email": "hod.cse@college.edu" }
```

Useful response fields FE already parses:

```json
{
  "id": 1,
  "name": "Computer Science",
  "code": "CSE",
  "hod_name": "…",
  "hod_email": "…",
  "hod_status": "invited",
  "activation_token": "…",
  "message": "Invite email sent."
}
```

(Also accepts nested `department` object.)

**Email (required):**

- Subject e.g. `Activate your MentorMuni HOD account — {College}`  
- Link: `{FRONTEND_ORIGIN}/activate-hod?token={token}`  
- College + department name; expiry (~72h)

**Config note:** `staff_activation_path` currently defaults to `/activate`. Set to `/activate-hod` (or make HOD emails use that path) so email links match `ActivateHodPage`.

### 3.5 Students — FE product contract (Enrollment still local)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/organizations/students/invite` | `{ emails: string[], department_id? }` |
| `GET` | `/organizations/students/invites?status=pending` | Approval queue |
| `POST` | `/organizations/students/invites/:id/approve` | |
| `POST` | `/organizations/students/invites/:id/reject` | |
| `POST` | `/organizations/students/import` | JSON bulk (see below) **or** keep CSV and document for FE |
| `GET` | `/organizations/students` | Roster (`department_id` filter) |
| `PATCH` | `/organizations/students/:id` | Reassign / disable |
| `POST` | `/students/register` | Self-register (already exists at this path) |

**Import JSON (preferred by sprint brief):**

```json
{
  "department_id": 3,
  "rows": [
    {
      "email": "rahul@college.edu",
      "name": "Rahul Sharma",
      "roll_number": "CSE21-042",
      "batch_year": 2025
    }
  ],
  "send_invite_email": true
}
```

**Import response:**

```json
{
  "created": 40,
  "updated": 2,
  "skipped": 1,
  "errors": [{ "row": 12, "email": "bad@", "message": "Invalid email" }]
}
```

Backend already has CSV `POST /users/import` → map or dual-support this sprint.

### 3.6 Notifications / audit / dashboard (FE expected)

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/organizations/notifications` | Current user inbox (`unread` filter) |
| `POST` | `/organizations/notifications/:id/read` | Mark read |
| `POST` | `/organizations/notifications/read-all` | |
| `GET` | `/organizations/audit-logs` | TPO; filters: action, actor, from/to, entity |
| `GET` | `/organizations/dashboard` | Counts + `by_department[]` |

**Minimum audit actions:**

`department.create|update|delete`  
`hod.invite|reinvite|revoke|replace|activate`  
`student.invite|import|approve|reject|register`  
`auth.password_change` (optional: `auth.login`)

---

## 4. Suggested tables (minimum) — status in this repo

| Table / concept | Status |
|-----------------|--------|
| `organizations`, `users`, `roles`, `permissions` | ✅ |
| `departments` (+ soft-delete) | ✅ — no HOD columns; HOD is a `users` row with `department_id` + `DEPARTMENT_ADMIN` |
| Activation tokens | ✅ — `users.activation_token_hash` (+ expiry fields as implemented), not a separate table |
| Student profiles / invites | Partial — students are `users` with `STUDENT`; PENDING approve/reject exists; no separate `student_invites` table |
| `notifications` + `notification_recipients` | ✅ |
| `audit_logs` | ✅ table + writer; list API missing |
| Email outbox | ❌ — sync send via `app.common.email` (same as TPO) |

---

## 5. Recommended ship plan (unblock live website)

Align to FE paths **without** forcing FE rewrite this sprint. Prefer thin aliases / nest routes that call existing services.

### P1 — Departments under `/organizations/departments`

- Mount aliases (or move router) so FE paths hit existing CRUD.  
- Enrich list/detail response with HOD derived from current `DEPARTMENT_ADMIN` user on that dept + `student_count`.  
- Soft-delete already exists; define policy if students present (see §9).

### P2 — HOD lifecycle on department

| Method | Path | Implementation sketch |
|--------|------|------------------------|
| `POST` | `/organizations/departments/{id}/hod` | Create `DEPARTMENT_ADMIN` on dept (reuse `users.service.create_user` + `send_hod_invite_email`); enforce **one active/invited HOD per dept** |
| `POST` | `…/hod/reinvite` | Rotate token + resend email |
| `POST` | `…/hod/revoke` | Disable HOD user; keep students; invalidate token |
| `POST` | `…/hod/replace` | Revoke old + invite new |
| `POST` | `/auth/activate-hod` | Alias → same handler as `/auth/activate` |
| Email link | `/activate-hod?token=` | Set `staff_activation_path=/activate-hod` (or HOD-specific builder) |

### P3 — Auth for HOD

Already works once user is ACTIVE + role `DEPARTMENT_ADMIN`. Verify login + me + change-password E2E after activate.

### P4 — Students

Minimum to leave localStorage:

1. `GET /organizations/students` → filter `role_code=STUDENT` (wrap `list_users`).  
2. `POST /organizations/students/import` → JSON rows **or** document CSV and wire Enrollment later.  
3. Invite queue: either introduce `student_invites` **or** treat PENDING `users` as the queue (`GET …?status=PENDING` + existing approve/reject).  
4. Keep `POST /students/register` as public self-register.

### P5 — Notifications

- Alias `GET /organizations/notifications` → inbox for current user.  
- HOD invite email can stay direct send this sprint; optionally also insert an in-app / audit trail row.  
- Full email-job worker is nice-to-have if sync mailer already works for TPO.

### P6 — Audit logs

- Call `write_audit` on department + HOD lifecycle mutates.  
- Add `GET /organizations/audit-logs` (TPO / `VIEW_REPORTS` or similar permission).

### P7 — Dashboard

- Alias `GET /organizations/dashboard` → existing identity funnel; optionally rename/alias fields FE metrics expect (`pending_invites` ← `students_pending`, `hod_status` on `by_department`).

---

## 6. End-to-end flows (acceptance)

### Flow A — HOD live (must pass)

```
TPO login
  → POST /organizations/departments
  → POST /organizations/departments/:id/hod { name, email }
  → Email received with /activate-hod?token=…
  → POST /auth/activate-hod { token, new_password }
  → POST /auth/login (HOD + organization_code)
  → GET /auth/me → role=DEPARTMENT_ADMIN, department_id set
  → UI: /Organization/dashboard
  → POST /auth/change-password works
```

Also verify: **reinvite**, **revoke** (old token invalid), **replace** (old HOD cannot login; new gets email).

### Flow B — Students import / invite

```
TPO → POST /organizations/students/import (or invite)
  → rows in DB + optional emails
  → GET /organizations/students shows roster
  → audit_logs contain student.import / student.invite
```

### Flow C — Notifications + audit visible

```
After HOD invite: email delivered (or activation_token returned if mail disabled)
TPO GET /organizations/audit-logs sees hod.invite
```

---

## 7. Explicitly NOT this sprint

- OpenAI / `POST /organizations/ai/campus-insight`  
- Full HOD batch ops UI (can be stub dashboard)  
- Program completion tracking / drive RSVP (can enqueue notify only)  
- Viewer/Director roles (optional later)

---

## 8. Slack / ticket paste for backend

> **Sprint:** Live TPO portal (real DB) — students register/import · HOD invite email · notifications · audit_logs.  
> **Success:** TPO creates department → invites HOD → HOD gets email → `/activate-hod` sets password → HOD logs into Organization Portal home; can change password. Students import/invite into departments. All writes audited; invite emails go through notifications/email jobs.  
> **APIs:** Departments CRUD under `/organizations/departments`; `…/hod` invite|reinvite|revoke|replace; `POST /auth/activate-hod`; students invite/import/list; notifications + audit-logs; `GET /organizations/dashboard` from DB.  
> **Note:** Core services largely exist (`/departments`, `/users`, `/auth/activate`, `/dashboard`, notifications table) — this sprint is **FE path/shape alignment + HOD lifecycle + student roster APIs + audit list**.  
> **Out of scope:** AI Campus Brief (next).  
> **Spec:** `docs/backend-tpo-sprint-live-apis.md` (this file)

---

## 9. Kickoff questions — recommended answers from current code

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Reuse activation tokens from TPO, or separate table? | **Reuse** `users.activation_token_hash` + `/auth/activate` (add `/auth/activate-hod` alias). Same pattern as TPO. |
| 2 | One HOD per department hard constraint? | **Yes** for invite/replace UX. Enforce in `…/hod` handlers (reject second invite unless revoke/replace). |
| 3 | Student import: create login immediately vs invite-only? | **Invite / PENDING** for self-register + email invites; **ACTIVE with temp/invite email** for TPO bulk import if `send_invite_email=true`, else PENDING/INVITED without password. Match existing approve flow where possible. |
| 4 | Mail provider for HOD? | **Same** as TPO (`app.common.email` + staff activation template). Point link at `/activate-hod`. |
| 5 | Soft-delete departments if students exist? | Soft-delete OK; **block hard empty requirement** — either refuse delete when active students exist, or soft-delete and leave students pointing at deleted dept (FE must handle). Prefer: **409 if active students**, allow delete if zero / only soft-deleted students. |

---

## 10. Priority order (copy for tickets)

1. Departments CRUD on **`/organizations/departments`** + HOD fields on payload  
2. HOD invite + email + **`/auth/activate-hod`** + login as HOD  
3. change-password (verify; already wired)  
4. Students invite/import + list (+ approve)  
5. notifications persistence + inbox alias (email worker optional if sync send works)  
6. audit_logs write on mutates + **list API**  
7. dashboard metrics alias from DB  

**Definition of live:** Flow A green on staging with real DB + real email; Enrollment can stay local until P4 lands.

---

## 11. Student enrollment APIs (shipped)

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/organizations/students?department_id=` | Roster (ACTIVE / INVITED / BLOCKED) |
| `GET` | `/organizations/students/invites?status=pending` | Approval queue |
| `POST` | `/organizations/students/invite` | `{ emails[], department_id, auto_enroll?/skip_approval? }` → PENDING **or** INVITED + email when flags set |
| `POST` | `/organizations/students` | Manual `{ name, email, department_id, roll_number?, batch_year?, auto_enroll?/skip_approval? }` → invitation **or** `{ student, emailed, setup_url?, activation_token?, message }` |
| `POST` | `/organizations/students/import` | JSON `rows[]` and/or `csv_text`; `auto_enroll`/`skip_approval`/`send_invite_email` → INVITED + emails |
| `POST` | `/organizations/students/invites/:id/approve` | → INVITED + set-password email (`emailed`, `setup_url`/`activation_token`, `message`) |
| `POST` | `/organizations/students/invites/:id/reject` | → REJECTED (cannot login) |
| `POST` | `/organizations/students/:id/resend-invite` | Rotate set-password token + email (`resend-setup` / `resend-activation` aliases) |
| `PATCH` | `/organizations/students/:id` | `name`, `roll_number`, `batch_year`, `status` (DISABLED→BLOCKED), `department_id` (TPO) |
| `POST` | `/auth/activate-student` | `{ token, new_password }` |

Migration: `0005_student_enrollment` adds `users.roll_number`, `users.batch_year`.

### Self-enroll from login (public)

| Method | Path | Auth | Notes |
|--------|------|------|--------|
| `GET` | `/organizations/colleges/{code}/departments` | API key | Active depts for enroll dropdown |
| `POST` | `/students/register` | API key | Body: `organization_code`, `department_id`, `name`, `email`, `roll_number?`, `phone?` → PENDING (no password). Idempotent if same email already PENDING. |
