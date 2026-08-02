# Platform Admin — backend contract (FE gap answers)

Answers for Platform Admin FE integration. Auth: `X-API-Key` on all routes;
Bearer platform JWT on `/platform/*` except login + TPO activate.

---

## 1. Edit org — full PUT beyond status?

**Yes.** `PUT /platform/organizations/{id}`

Body (all optional; send only fields to change):

| Field | Type | Notes |
|-------|------|--------|
| `name` | string | |
| `code` | string | uppercased; unique; PUBLIC locked |
| `organization_type` | `COLLEGE` \| `PUBLIC` | PUBLIC org type locked |
| `status` | `ACTIVE` \| `SUSPENDED` | PUBLIC cannot be suspended |
| `contact_person`, `contact_email`, `contact_phone` | | |
| `address`, `city`, `state`, `country` | | |

Also: `GET /platform/organizations/{id}` for detail drawer.

---

## 2. Delete org — allowed? soft vs hard?

**Allowed as soft-delete only.** `DELETE /platform/organizations/{id}`

- Sets `status=SUSPENDED`
- Cancels all `ACTIVE` subscriptions → `CANCELLED`
- Returns the updated org (not 204 empty)
- **Blocked** for PUBLIC / MentorMuni Public (`400`)
- Hard delete of rows is **not** supported (FK graph: users, depts, features)

Alternative: `PUT` with `{ "status": "SUSPENDED" }` only (does not auto-cancel subs).

---

## 3. Subscription renew — POST vs PUT?

| Case | Method |
|------|--------|
| First assign (no ACTIVE) | `POST /platform/subscriptions` |
| Renew / change plan on existing ACTIVE | `PUT /platform/subscriptions/{id}` |

**PUT body:** `plan_id`, `student_limit`, `start_date`, `end_date`, `status` (`ACTIVE`\|`EXPIRED`\|`CANCELLED`)

Cancel from UI: `PUT …/{id}` with `{ "status": "CANCELLED" }` (or `EXPIRED`).

`POST` while an ACTIVE exists still works (expires old ACTIVE → creates new row). Prefer **PUT** to keep the same subscription id / history continuity.

---

## 4. `/subscription-plans` — auth? canonical IDs?

`GET /subscription-plans`

| Auth | Required? |
|------|-----------|
| `X-API-Key` | **Yes** |
| Bearer JWT | **No** |

Response fields (use these; do not hardcode 1/2/3):

```json
{
  "id": 3,
  "plan_code": "ENTERPRISE",
  "plan_name": "Enterprise",
  "plan_type": "COLLEGE",
  "duration_months": 12,
  "max_students": 1500,
  "price": "0.00",
  "status": "ACTIVE",
  "created_at": "..."
}
```

**Canonical `plan_code` values (stable across envs):**

| plan_code | plan_name | type | max_students |
|-----------|-----------|------|--------------|
| `STARTER` | Starter | COLLEGE | 200 |
| `GROWTH` | Growth | COLLEGE | 800 |
| `ENTERPRISE` | Enterprise | COLLEGE | 1500 |
| `PREMIUM_STUDENT` | Premium Student | INDIVIDUAL | 1 |

FE must call this endpoint and use returned `id` (or match by `plan_code`) when assigning subscriptions. Numeric `id` may differ per DB; `plan_code` does not.

---

## 5. Platform user update — fields beyond status?

**Yes.** `PUT /platform/users/{id}` (PLATFORM_ADMIN only)

| Field | Notes |
|-------|--------|
| `name` | |
| `email` | unique |
| `role` | `PLATFORM_ADMIN` \| `SUPPORT` \| `SALES` \| `OPERATIONS` |
| `status` | `ACTIVE` \| `INACTIVE` |
| `password` | optional; sets `must_change_password=true` |

Also: `DELETE /platform/users/{id}` → soft `INACTIVE`. Invite = `POST /platform/users` with temp password (forces password change).

`GET /platform/auth/me` includes `must_change_password`.

---

## 6. 401 / 403 + token expiry contract

**No refresh endpoint.** Login returns `expires_in_minutes`; FE must re-login after expiry.

Error body shape:

```json
{
  "detail": {
    "code": "TOKEN_EXPIRED",
    "message": "Token expired. Please log in again."
  }
}
```

| HTTP | `detail.code` | When | FE action |
|------|---------------|------|-----------|
| 401 | `INVALID_API_KEY` | Bad/missing `X-API-Key` | Fix env key |
| 401 | `TOKEN_MISSING` | No Bearer | Logout → login |
| 401 | `TOKEN_EXPIRED` | JWT past `exp` | Logout → login |
| 401 | `TOKEN_INVALID` | Bad/forged/wrong subject | Logout → login |
| 401 | `TOKEN_WRONG_SCOPE` | Tenant token on platform route | Logout → login |
| 401 | `INVALID_CREDENTIALS` | Bad login email/password | Show error |
| 403 | `ACCOUNT_INACTIVE` | User/platform account inactive | Logout / show blocked |
| 403 | `FORBIDDEN_ROLE` | Role not allowed for route | Show permission error (keep session) |
| 403 | `ORG_SUSPENDED` | College suspended (tenant) | Show message |

FE auto-logout on **401** (and 403 only when message/code is token-related). Do **not** auto-logout on `FORBIDDEN_ROLE`.

---

## Out of scope (confirmed)

- HOD creation from Platform → TPO in org portal
- Student ops / college dashboards → org portal only
