# Frontend Task: Resume ATS Score UI (MentorMuniUI)

Use this document as the implementation brief for the Resume ATS page. Backend changes are live on `POST /api/resume/ats`.

---

## Goal

Upgrade the Resume ATS results experience to match (and exceed) Naukri Resume Quality Score — show **scores**, **Naukri checklist**, **copy-ready rewrites**, and **portal tips** in a clear tabbed layout.

---

## 1. API Request (multipart/form-data)

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `file` | Yes | File | `.pdf`, `.doc`, `.docx` — max 5 MB |
| `target_role` | Yes | string | e.g. `"Java Backend Developer"` |
| `candidate_type` | No | string | `college_student` \| `experienced` \| `fresher` |
| `experience_years` | No | number | 0–50 |
| `job_description` | No | string | Paste JD text for better keyword matching |

```javascript
const formData = new FormData();
formData.append("file", file, file.name);
formData.append("target_role", targetRole);
if (candidateType) formData.append("candidate_type", candidateType);
if (experienceYears != null) formData.append("experience_years", String(experienceYears));
if (jobDescription?.trim()) formData.append("job_description", jobDescription.trim());

const res = await fetch(`${API_BASE}/api/resume/ats`, { method: "POST", body: formData });
const data = await res.json();
const normalized = normalizeAtsResponse(data);
```

**Loading UX:** Expect 3–10 seconds when LLM enrichment is on. Show steps: “Extracting text…” → “Scoring resume…” → “Generating recommendations…”

---

## 2. Response fields to render

### Core scores (always present)

| Field | UI |
|-------|-----|
| `score` | Main gauge 0–100 |
| `score_label` | Badge: **Strong** (80+), **Moderate** (60–79), **Low** (&lt;60) |
| `keywords`, `formatting`, `impact`, `ats` | Four sub-score bars or rings |
| `skills_count` | “X skills detected” (target: 10–15) |

**Disclaimer (required):**  
> Scores are directional estimates for resume + Naukri visibility — not Naukri’s exact Profile Score.

### Naukri readiness (new)

```json
"naukri_readiness": {
  "resume_document": 72,
  "profile_alignment": 68,
  "label": "Moderate",
  "visibility_band": "60–79 — moderate; many recruiters filter below 70 on Naukri..."
}
```

Show two side-by-side cards:
- **Resume document score** → `resume_document`
- **Naukri alignment score** → `profile_alignment` + `visibility_band`

### Section scores (new)

```json
"section_scores": {
  "headline": 60,
  "summary": 75,
  "experience": 80,
  "skills": 85,
  "education": 70,
  "contact": 90
}
```

Render as a horizontal bar chart or 6 mini-gauges.

### Naukri checklist (new)

```json
"naukri_checklist": [
  { "item": "10–15 key skills listed", "status": "pass", "current": 12, "target": 15, "detail": "..." }
]
```

| `status` | UI |
|----------|-----|
| `pass` | Green check |
| `warn` | Amber warning |
| `fail` | Red X |

Show `current` / `target` when present (e.g. skills 6/15).

### Format warnings (new)

```json
"format_warnings": [
  { "code": "few_skills", "message": "...", "severity": "warn" }
]
```

Show as alert banners above results (`fail` = red, `warn` = amber).

### Keywords

- `matched_keywords` → green chips
- `missing_keywords` → red chips
- `keyword_gaps` (LLM) → amber chips with placement hint text

### Coaching text

| Field | Section |
|-------|---------|
| `summary` | Top narrative card |
| `top_resume_killers` | “Top issues” (3 bullets, red accent) |
| `priority_action_plan` | Numbered list, highest impact first |
| `strengths` | “What’s working” |
| `fixes` | “Resume fixes” |
| `portal_tips` | “Naukri & LinkedIn” tab |
| `rewrite_examples` | Expandable before/after cards |

### Copy-ready rewrites (LLM — high value)

```json
"section_rewrites": {
  "headline": "2+ Years Java Backend Developer | Spring Boot | Microservices",
  "summary": "...",
  "skills": "Java, Spring Boot, REST, ...",
  "project_or_experience": ["Bullet 1...", "Bullet 2..."]
}
```

Each block needs a **Copy** button (`navigator.clipboard.writeText`).

### Optional LLM extras

| Field | UI |
|-------|-----|
| `inferred_role` | Show if different from user-selected role |
| `candidate_type` | Badge: Fresher / Experienced |
| `score_breakdown` | Four `/10` pills (keyword, impact, structure, ats_readability) |
| `ats_score_estimate` | Secondary card: score + label + reason |

---

## 3. Suggested page layout

```
┌─────────────────────────────────────────────────────────┐
│  [Target role ▼]  [Candidate type ▼]  [Years exp]       │
│  [Job description (optional) ─────────────────────]     │
│  [Upload resume]  [Analyze Resume]                      │
└─────────────────────────────────────────────────────────┘

After submit:
┌──────────────┬──────────────────────────────────────────┐
│ Overall 72   │  Strong / Moderate / Low badge             │
│ Moderate     │  naukri_readiness.visibility_band          │
├──────────────┴──────────────────────────────────────────┤
│ Tabs: [Scores] [Fix Resume] [Naukri & LinkedIn] [Copy]  │
├─────────────────────────────────────────────────────────┤
│ Scores tab: sub-scores + section_scores + checklist     │
│ Fix tab: killers, fixes, priority_action_plan, rewrites │
│ Portal tab: portal_tips + checklist fail items          │
│ Copy tab: section_rewrites with copy buttons            │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Update `normalizeAtsResponse`

Extend the normalizer with safe defaults so older API responses don’t break:

```javascript
function normalizeAtsResponse(raw) {
  const score = Number(raw?.score ?? 0);
  return {
    score,
    score_label: raw?.score_label ?? (score >= 80 ? "Strong" : score >= 60 ? "Moderate" : "Low"),
    ats: Number(raw?.ats ?? 0),
    keywords: Number(raw?.keywords ?? 0),
    formatting: Number(raw?.formatting ?? 0),
    impact: Number(raw?.impact ?? 0),
    summary: raw?.summary ?? "",
    matched_keywords: raw?.matched_keywords ?? [],
    missing_keywords: raw?.missing_keywords ?? [],
    fixes: raw?.fixes ?? [],
    strengths: raw?.strengths ?? [],
    portal_tips: raw?.portal_tips ?? [],
    skills_count: Number(raw?.skills_count ?? 0),
    section_scores: raw?.section_scores ?? {
      headline: 0, summary: 0, experience: 0, skills: 0, education: 0, contact: 0,
    },
    naukri_checklist: raw?.naukri_checklist ?? [],
    naukri_readiness: raw?.naukri_readiness ?? {
      resume_document: score,
      profile_alignment: score,
      label: raw?.score_label ?? "Moderate",
      visibility_band: "",
    },
    format_warnings: raw?.format_warnings ?? [],
    // LLM optional
    candidate_type: raw?.candidate_type ?? null,
    inferred_role: raw?.inferred_role ?? null,
    top_resume_killers: raw?.top_resume_killers ?? [],
    keyword_gaps: raw?.keyword_gaps ?? [],
    rewrite_examples: raw?.rewrite_examples ?? [],
    section_rewrites: raw?.section_rewrites ?? null,
    priority_action_plan: raw?.priority_action_plan ?? [],
    score_breakdown: raw?.score_breakdown ?? null,
    ats_score_estimate: raw?.ats_score_estimate ?? null,
    job_description_provided: Boolean(raw?.job_description_provided),
  };
}
```

---

## 5. Form fields to add

| UI control | Maps to |
|------------|---------|
| Target role dropdown / input | `target_role` |
| “I am a…” select: Fresher / Student / Experienced | `candidate_type` |
| Years of experience (number) | `experience_years` |
| Optional “Paste job description” textarea | `job_description` |
| File upload | `file` |

---

## 6. Error handling

| Status | Message |
|--------|---------|
| 422 | Show `detail` — includes non-resume file, bad type, invalid `candidate_type` |
| 413 | “File too large (max 5 MB)” |
| 429 | “Too many requests — wait a minute” |
| 500 | Generic retry message |

---

## 7. Acceptance criteria

- [ ] Form sends all three optional fields when filled
- [ ] Overall score + `score_label` badge visible
- [ ] Four sub-scores + six `section_scores` rendered
- [ ] `naukri_checklist` with pass/warn/fail icons
- [ ] `naukri_readiness` two-score card + visibility band text
- [ ] `format_warnings` shown as banners when non-empty
- [ ] Matched / missing keyword chips
- [ ] Tabbed layout: Scores | Fix Resume | Naukri & LinkedIn | Copy blocks
- [ ] `section_rewrites` copy buttons work
- [ ] `normalizeAtsResponse` handles missing optional LLM fields
- [ ] Loading state for 3–10s LLM latency
- [ ] Disclaimer that score is directional, not Naukri’s exact score

---

## 8. Files likely to touch (MentorMuniUI)

- Resume ATS page HTML (e.g. `resume-ats.html` or section in tools page)
- `resume-ats.js` or shared API module
- `normalizeAtsResponse` helper
- CSS for score gauges, checklist, tabs

---

## 9. Copy-paste prompt for frontend agent

```
Implement the Resume ATS results UI per docs/RESUME_ATS_FRONTEND_TASK.md in MentorMuniAPI.

Backend: POST /api/resume/ats (multipart) — fields: file, target_role, optional candidate_type, experience_years, job_description.

Must render: score + score_label, 4 sub-scores, section_scores (6 bars), naukri_readiness card, naukri_checklist with pass/warn/fail, format_warnings banners, keyword chips, tabbed sections (Scores | Fix Resume | Naukri & LinkedIn | Copy rewrites).

LLM fields (optional in response): top_resume_killers, priority_action_plan, section_rewrites with copy buttons, keyword_gaps, ats_score_estimate, score_breakdown.

Extend normalizeAtsResponse with defaults from the doc. Add form fields for candidate_type, experience_years, job_description. Loading state 3–10s. Show disclaimer that scores are directional.
```
