# TPO / HOD AI deep analysis APIs

**Audience:** Organization Portal frontend (`/Organization/*`)  
**Backend module:** `app/org_performance/insight.py`  
**Model default:** `gpt-4.1-mini` (`ORG_PERFORMANCE_INSIGHT_MODEL` env)  
**Fallback:** Rule-based heuristic when `OPENAI_API_KEY` is missing or the call fails

---

## Auth

All endpoints require:

| Header | Value |
|--------|--------|
| `X-API-Key` | Platform org API key |
| `Authorization` | `Bearer <org JWT>` |

**Permissions**

| Endpoint | TPO | HOD |
|----------|-----|-----|
| `POST /organizations/ai/campus-insight` | ✅ | ❌ (403) |
| `POST /organizations/ai/branch-insight` | ✅ (`department_id` required) | ✅ (own dept) |
| `POST /organizations/ai/student-insight/{id}` | ✅ | ✅ (own dept students) |

---

## 1. Campus insight (TPO)

```http
POST /organizations/ai/campus-insight
Content-Type: application/json

{
  "include_leaderboard": true,
  "max_actions": 5,
  "focus_area": "overall",
  "department_id": null
}
```

Optional `department_id` filters campus view to one branch.  
`focus_area`: `overall` | `aptitude` | `skills` | `interview` | `communication` | `technical` | `shortlist` | `snap`

**Response shape**

```json
{
  "ok": true,
  "source": "openai",
  "model": "gpt-4.1-mini",
  "generated_at": "2026-08-31T13:30:00+00:00",
  "cache_ttl_seconds": 900,
  "organization_id": 1,
  "department_id": null,
  "scope": "organization",
  "metrics": { },
  "insight": {
    "summary": "…",
    "going_well": ["…"],
    "concerns": ["…"],
    "actions": ["Assign …", "Run …"],
    "shortlist_notes": ["…"]
  }
}
```

`source` is `"heuristic"` when OpenAI is unavailable.

---

## 2. Branch insight (HOD / TPO drill-down)

```http
POST /organizations/ai/branch-insight
Content-Type: application/json

{
  "include_leaderboard": true,
  "max_actions": 5,
  "focus_area": "skills",
  "department_id": 3
}
```

- **HOD:** `department_id` is ignored; server uses the HOD's linked department.
- **TPO:** `department_id` is **required**.

Same response shape as campus insight with `scope: "department"`.

---

## 3. Student insight (scorecard drawer)

```http
POST /organizations/ai/student-insight/42
Content-Type: application/json

{
  "max_actions": 5,
  "focus_area": "overall",
  "include_dept_context": true
}
```

**Response**

```json
{
  "ok": true,
  "source": "openai",
  "model": "gpt-4.1-mini",
  "generated_at": "2026-08-31T13:30:00+00:00",
  "cache_ttl_seconds": 900,
  "organization_id": 1,
  "student_id": 42,
  "student_name": "Rahul Sharma",
  "department_id": 3,
  "department_name": "Computer Science",
  "scope": "organization",
  "metrics": { "student": { }, "dept_context": { } },
  "insight": {
    "summary": "…",
    "going_well": ["strength bullets"],
    "concerns": ["gap bullets"],
    "actions": ["TPO/HOD follow-ups"],
    "shortlist_notes": ["drive verdict + student next steps"]
  }
}
```

**Field mapping for student UI**

| `insight` field | Show as |
|-----------------|---------|
| `going_well` | Strengths |
| `concerns` | Gaps / risks |
| `actions` | Recommended for TPO/HOD |
| `shortlist_notes` | Drive readiness + student next steps |

---

## Supporting data APIs (no LLM)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/organizations/performance/summary` | Dashboard aggregates + clarity board |
| `GET` | `/organizations/performance/scorecards` | All student scorecards |
| `GET` | `/organizations/performance/scorecards/{id}` | Single student (drawer) |

Use **summary + charts** for always-on UI. Call **insight** endpoints on demand (button click) to control OpenAI cost.

---

## Portal separation (TPO vs HOD)

AI insight is **not shared across roles**. Each portal calls only its own API:

| Portal | URL prefix | AI panel component | Backend endpoint |
|--------|------------|-------------------|------------------|
| **TPO** | `/Organization/tpo/*` | `TpoCampusInsightPanel` | `POST /organizations/ai/campus-insight` |
| **HOD** | `/Organization/hod/*` | `HodBranchInsightPanel` | `POST /organizations/ai/branch-insight` |
| **Both** | scorecard drawer | `StudentAiInsight` | `POST /organizations/ai/student-insight/{id}` |

After login, users are routed automatically:

- TPO (`role: TPO` / `ORG_ADMIN`) → `/Organization/tpo/dashboard`
- HOD (`role: HOD` / `DEPARTMENT_ADMIN`) → `/Organization/hod/dashboard`

`RequireRole` blocks cross-portal access (HOD cannot open `/Organization/tpo/*`).

---

## Frontend wiring

Reference implementation:

```
Frontend/src/organizationPortal/
  OrganizationRoutes.jsx      # /Organization/* routes + role guards
  pages/tpo/                  # TPO-only pages
  pages/hod/                  # HOD-only pages
  components/TpoCampusInsightPanel.jsx
  components/HodBranchInsightPanel.jsx
  components/StudentAiInsight.jsx
```

### TPO portal only

```jsx
import { TpoCampusInsightPanel } from '../organizationPortal';

// Inside /Organization/tpo/dashboard or performance page only
<TpoCampusInsightPanel />
```

### HOD portal only

```jsx
import { HodBranchInsightPanel } from '../organizationPortal';

// Inside /Organization/hod/dashboard or performance page only
<HodBranchInsightPanel />
```

### Student drawer (either portal)

```jsx
import { StudentAiInsight } from '../organizationPortal';

<StudentAiInsight studentId={student.id} studentName={student.name} />
```

---

## Cost notes

- Campus / branch brief: ~1 call per refresh (~1100 tokens out)
- Student brief: ~1 call per student open (~900 tokens out)
- Use `gpt-4.1-mini` for all org insight (default)
- Do **not** auto-poll; regenerate on user action only
