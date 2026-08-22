# Forgot / reset password (Org · Mentormuni · Student)

All portals use the same APIs. User enters **username (college ID) or email**;
reset link is emailed to the account’s registered address.

## Request reset

`POST /auth/forgot-password`

```json
{
  "identifier": "rahul@college.edu",
  "organization_code": "MEDICAPS",
  "portal": "organization"
}
```

Also accepts `email` and/or `username` instead of `identifier`.

| `portal` | Reset link path |
|----------|-----------------|
| `organization` (default) | `/Organization/reset-password?token=…` |
| `student` | `/studentportal/reset-password?token=…` |

Response:

```json
{
  "message": "If an account exists for those details, a reset link has been sent.",
  "emailed": true,
  "reset_url": null
}
```

If mail fails: `emailed: false` and `reset_url` is **always null** on this public endpoint
(never return a usable reset link to unauthenticated callers). Staff must use email or a
separate authenticated ops path to share links.
Always returns 200 with a generic message (does not leak whether the account exists).

Only **ACTIVE** accounts with a password can reset.

## Complete reset

`POST /auth/reset-password`

```json
{ "token": "…", "new_password": "newSecurePass1" }
```

## Frontend pages

| Portal | Forgot | Reset |
|--------|--------|-------|
| Organization / Mentormuni | `/Organization/forgot-password` | `/Organization/reset-password` |
| Student | `/studentportal/forgot-password` | `/studentportal/reset-password` |

Legacy `/forgot-password` and `/reset-password` redirect to the Organization pages.
