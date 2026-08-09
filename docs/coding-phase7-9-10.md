# Coding assessment — Phases 9 & 10 (finished)

## Phase 9 — Results / learning UX

- Official vs coaching scores clearly labeled
- Progressive coaching disclosure with:
  - dimension scores (correctness, approach, complexity, quality, edge cases)
  - strengths, learning gaps, next focus, mistakes
  - better approach + constraint awareness
- Past results revisit via `GET /api/coding/submissions` + in-widget History tab
- Practice again from results

## Phase 10 — Company-aware intelligence (student-safe)

API:
- Assessments ranked by internal `evidence_confidence` (never returned raw)
- Filter: `GET /api/coding/assessments?company_key=microsoft`
- Student-safe fields: `relevance_label`, `why_this_matters`, `topic`, `pattern`, `placement_blurb`
- `evidence_json` / `evidence_notes` / raw confidence remain forbidden

UI / portal:
- Coding widget company picker when launched with `mode=<company_key>`
- Practice tools catalog includes Coding
- Company Prep mission includes coding pattern drill (company-keyed when known)
- Company Intel page CTA → coding patterns for that company

Still intentional non-goals: AI question generation, exposing raw evidence payloads.
