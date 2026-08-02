# TPO → HOD E2E backend contract (locked for FE)

Auth on org JWT routes: `Authorization: Bearer <token>` + `X-API-Key`.  
Activate routes: **API key only** (no JWT).

**One-liner:** FE is ready for the locked TPO→dept→HOD contract. Deploy through **0008**, real HOD/TPO emails with `emailed`+token/url, colleges listing ACTIVE orgs (incl. new ones), activate returning `organization_code`, and stable 409/403/duplicate error codes.

---

## Must-have checklist (BE answers)

### 1. Migrations through 0008

| Rev | Purpose |
|-----|---------|
| 0006 (`0006_plat_must_chg_pwd`) | `platform_users.must_change_password` |
| 0007 | `subscription_plans.plan_code` + Starter/Growth/Enterprise |
| **0008** | `users.must_change_password` |

Deploy Alembic to head on the env that `VITE_API_URL` points at before FE E2E.

### 2. SMTP / invite email (HOD + TPO)

**HOD** `POST …/hod`, `/reinvite`, `/replace` always return:

```json
{
  "message": "...",
  "emailed": true,
  "activation_token": "<raw>",
  "activation_url": "https://…/activate-hod?token=…",
  "department": { /* enriched */ }
}
```

| SMTP | `emailed` | token + url |
|------|-----------|-------------|
| Sent OK | `true` | **always present** (ops fallback) |
| Off / fail | `false` | **always present** — never silent success without either |

**TPO** Platform create/reinvite already returns `email_sent`, `email_skipped`, `email_detail`, `activation_token`, `activation_url`.

Default invite TTL: **72 hours**. Expired activate → `400` + `ACTIVATION_TOKEN_EXPIRED`.

### 3. `GET /organizations/colleges`

Returns every **ACTIVE** `organization_type=COLLEGE` (excludes PUBLIC + SUSPENDED by default).

| Prerequisite | Required for list? |
|--------------|--------------------|
| Subscription / plan | **No** |
| Feature flags | **No** |
| TPO invited/activated | **No** |

**Rule:** As soon as PA creates an org with `status=ACTIVE`, it appears in colleges. Assigning a plan/features is independent (needed for product usage, not for login picker).

`?include_suspended=true` also returns SUSPENDED colleges.

### 4. Activate → `organization_code`

| Endpoint | Response |
|----------|----------|
| `POST /platform/auth/activate-tpo` | `{ message, organization_code }` |
| `POST /auth/activate-hod` | `{ message, organization_code }` |

FE can route to `/Organization/login?org=CODE`.

**Password rule:** Activate sets the user’s chosen password and sets `must_change_password=false`. **No second forced change** after activate. Forced change is only for Platform-created staff passwords / admin password resets.

### 5. Structured invite / mutate errors

Shape: `{ "detail": { "code": "…", "message": "…" } }`

| Situation | HTTP | `code` |
|-----------|------|--------|
| Duplicate HOD email / email is TPO | 409 | `HOD_EMAIL_CONFLICT` |
| Email already live HOD on another dept | 409 | `HOD_EMAIL_IN_USE` |
| Dept already has live HOD | 409 | `HOD_ALREADY_ASSIGNED` |
| Delete dept with students | 409 | `DEPARTMENT_HAS_STUDENTS` |
| HOD calling dept/HOD mutate | 403 | `FORBIDDEN_ROLE` |
| Dept code clash | 409 | `DEPARTMENT_CODE_EXISTS` |
| Bad/used activate token | 400 | `ACTIVATION_TOKEN_INVALID` |
| Expired activate token | 400 | `ACTIVATION_TOKEN_EXPIRED` |
| Bad login | 401 | `INVALID_CREDENTIALS` |
| Suspended org login | 403 | `ORG_SUSPENDED` |

### 6. Login / me smoke

- Login: `role: "TPO"|"HOD"`, `access_token`, `expires_in_minutes`, nested `user`
- `/auth/me`: org fields + for HOD `department_id` / `department_name` / `department_code` + `must_change_password`
- JWT embeds `org_id`, `department_id`, DB `role_code`

---

## Auth detail

### `/auth/me` + `login.user`

```json
{
  "id": 1,
  "name": "Priya Sharma",
  "email": "hod@college.edu",
  "role": "HOD",
  "role_code": "DEPARTMENT_ADMIN",
  "organization_id": 10,
  "organization_name": "ABC College",
  "organization_code": "ABC",
  "department_id": 3,
  "department_name": "Computer Science",
  "department_code": "CSE",
  "permissions": ["VIEW_DEPARTMENT_STUDENTS"],
  "must_change_password": false
}
```

Aliases: `ORG_ADMIN` → `TPO`, `DEPARTMENT_ADMIN` → `HOD`.

---

## Departments + HOD

| Method | Path | Who |
|--------|------|-----|
| CRUD | `/organizations/departments` | TPO only |
| Invite / reinvite / revoke / replace | `…/:id/hod*` | TPO only |

- One live HOD (`INVITED`|`ACTIVE`) per department — enforced server-side  
- Email unique per org — enforced server-side  
- Soft-delete department; students block with `DEPARTMENT_HAS_STUDENTS`  
- `mentor_history` from audit on department GET (populated after invite/activate/revoke/replace)

---

## Staging smoke

1. PA create org (ACTIVE) → appears in `GET /organizations/colleges`  
2. Invite TPO → email / token → `activate-tpo` → `organization_code`  
3. Login TPO with org code → JWT + `/auth/me`  
4. Create department → invite HOD → inbox / token → `activate-hod` → HOD login with `department_id`  
5. Confirm HOD cannot mutate departments (403)

Share this doc + production/staging `VITE_API_URL` with FE.
