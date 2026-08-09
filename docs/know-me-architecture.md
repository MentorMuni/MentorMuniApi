# Know Me — Private Student Self-Discovery

**Know Me** is a private, judgment-free sanctuary for students to reflect on their placement journey without fear of judgment or visibility to TPO/HOD.

## Product Principles

1. **Not an assessment** — feels like WhatsApp + elder brother + private journal
2. **Private by design** — no TPO/HOD access; separate DB tables enforce this
3. **Conversational, not clinical** — no "anxiety" or "fear test" language
4. **Empathy-first** — landing state validates before questions
5. **Action-oriented** — converts fears into concrete MentorMuni steps

## Architecture

### Backend

**Tables** (separate from roadmap/org performance):
- `private_student_checkins` — parent session
- `private_student_responses` — individual question responses
- `private_student_insights` — AI-generated elder-brother insights
- `private_student_progress` — optional 30–45 day progress tracking

**Routes** (`/student/know-me/*`, STUDENT-only):
- `POST /student/know-me/start` — create new check-in
- `POST /student/know-me/step/{checkin_id}` — save one step response
- `POST /student/know-me/insight/{checkin_id}` — generate elder-brother insight
- `GET /student/know-me/progress` — compare first vs. latest check-in

**Authorization**: All routes enforce `require_roles(RoleCode.STUDENT.value)`. TPO/HOD get 401. No role-based UI filtering; strict auth layer.

### Frontend

**Pages**:
- `StudentKnowMePage.jsx` — full multi-step flow

**Flow**:
1. **Landing** — empathy hero + privacy pledge
2. **Form** — 8 multi-part questions (placement pressure → technical → projects → friends → family → main fear → anything else)
3. **Result** — elder-brother response (headline + narrative + blockers + action plan)
4. **Progress** — optional 30–45 day growth view

**Storage**: Device-only (`localStorage`), not sent to org APIs.

## Questions (8 screens)

1. **Placement pressure** — multi-select fears
2. **Communication & speaking** — interview scenario
3. **Technical confidence** — honest self-assessment
4. **Projects & depth** — interview readiness
5. **Friends & comparison** — FOMO normalization
6. **Home & family** — outside pressure (optional)
7. **Main fear** — the thing they're most afraid to ask
8. **Anything else** — free text for non-categorical struggles

## Response Format

```json
{
  "checkin_id": 123,
  "source": "openai|heuristic",
  "headline": "One-liner that names their main challenge",
  "what_i_hear": ["statement 1", "statement 2", "statement 3"],
  "narrative": "2-3 paragraphs like a real senior would write",
  "blockers": [
    {
      "order": 1,
      "title": "What they're stuck on",
      "student_quote": "Their own words (or synthesized)",
      "mentormuni_action": "Concrete step in MentorMuni"
    }
  ],
  "action_plan": [
    {
      "priority": 1,
      "action_type": "Assessment|Skill|Mock|Drill",
      "description": "What they do this week",
      "tool_code": "aptitude|skill_readiness|interview_mock|null",
      "duration_minutes": 25
    }
  ],
  "call_to_action": "One warm encouraging sentence",
  "closing_line": "Final warm line"
}
```

## Config

**Backend** (`app/core/config.py`):
- `KNOW_MY_FEAR_MODEL` (default: `gpt-4.1`)

**Prompt** (`app/know_my_fear/insight_prompt.py`):
- System: elder-brother voice; validates + reframes + empowers
- User: student's answers across all 8 steps

## Privacy Enforcement

✅ **Auth layer** — only STUDENT role can call `/student/know-me/*`  
✅ **Separate tables** — never joined with org/roadmap tables  
✅ **No org endpoints** — TPO/HOD cannot query private data  
✅ **Device storage** — responses cached locally, never persisted to org  
✅ **UI respect** — lock icon + "Private to you" on every screen  

## Roadmap (Optional)

- **30–45 day re-check** — "How has this changed?" + growth viz
- **AI Mentor integration** — private context from Know Me → personalized voice coaching
- **Strength identification** — flip the script ("What's going right?")
