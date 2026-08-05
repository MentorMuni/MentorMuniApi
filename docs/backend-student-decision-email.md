# Student enrollment Approve / Deny emails

Frontend already sends `send_email: true` and reads `emailed` + `setup_url`.
Demo mode does not hit these APIs; real org JWT sessions do.

Uses the same mailer as HOD/TPO activation emails (`app.common.email`).

## 1. Approve

`POST /organizations/students/invites/{id}/approve`

Body:

```json
{ "send_email": true }
```

- Approves the pending request and puts the student on the roster (needs password).
- Creates a set-password / activation token (72h).
- Emails the student at their registered address with the set-password link
  (`/studentportal/set-password?token=…`).

Response:

```json
{
  "emailed": true,
  "email_sent": true,
  "setup_url": "https://…/studentportal/set-password?token=…",
  "activation_token": "…",
  "student": { "email": "student@college.edu", "name": "…" },
  "message": "Approved. Set-password email sent."
}
```

If mail fails: `"emailed": false` and still return `setup_url` / `activation_token`
so staff can share the link.

`send_email: false` skips the mail but still creates the token and returns `setup_url`.

## 2. Deny

`POST /organizations/students/invites/{id}/reject`

Body:

```json
{ "send_email": true }
```

- Marks the request rejected.
- Emails the student that enrollment was not approved (no password link).

Response:

```json
{
  "emailed": true,
  "email_sent": true,
  "message": "Denied. Notification email sent.",
  "invitation": { "id": 1, "email": "…", "status": "rejected", "…" }
}
```

If mail fails: `"emailed": false`.

## 3. Email content (minimum)

| Event   | Include |
|---------|---------|
| Approve | College name, set-password URL, expiry note |
| Deny    | College / dept name, request denied, contact HOD/TPO |

Templates: `render_student_activation_email`, `render_student_enrollment_denied_email`
in `app/common/email/templates.py`.
