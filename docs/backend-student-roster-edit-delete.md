# Student roster edit + delete

TPO/HOD fix wrong student details and remove bad roster entries.
Frontend Enrollment (TPO) and Students (HOD) pages are ready.

Approve / deny emails: see `docs/backend-student-decision-email.md`.

## 1. Update student

`PATCH /organizations/students/{id}`

Auth: org JWT (TPO / HOD) + API key. Permissions: `MANAGE_USER_STATUS` | `UPLOAD_STUDENTS` | `APPROVE_STUDENT`.

Body (all optional):

```json
{
  "name": "Rahul Sharma",
  "email": "rahul@college.edu",
  "phone": "9009355103",
  "roll_number": "0101ec",
  "batch_year": 2025,
  "department_id": 12,
  "status": "BLOCKED"
}
```

Also accepts `contact` / `mobile` as aliases for phone.

Response:

```json
{
  "student": {
    "id": 1,
    "name": "Rahul Sharma",
    "email": "rahul@college.edu",
    "phone": "9009355103",
    "roll_number": "0101ec",
    "batch_year": 2025,
    "department_id": 12,
    "department_name": "Electronics",
    "status": "active"
  },
  "message": "Student updated."
}
```

Notes:

- `email` / `phone` / `roll_number` are strings (roll can be alphanumeric).
- `department_id` is integer. **HOD cannot reassign department** (403); TPO can move across departments in the org.
- Unique `email` and `roll_number` within the org → **409** on conflict.
- FE `DISABLED` / `Inactive` → stored as `BLOCKED` (blocks login; does not delete).

## 2. Delete student

`DELETE /organizations/students/{id}`

Auth: same as update.

Soft-deletes the student and frees email/username so they can re-enroll later.
Leaves the roster (`deleted_at` set; status `BLOCKED`).

Response:

```json
{ "ok": true, "message": "Student removed." }
```

- **404** if missing / already deleted  
- **403** if HOD tries another department or wrong org
