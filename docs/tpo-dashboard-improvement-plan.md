# TPO Dashboard improvement plan

## Goal

**Dashboard** = at-a-glance command center (10-second situational awareness)  
**Performance** = deep analysis (branch compare, shortlists, filtered students)

## Phase 1 — Command center (Dashboard) ✅ implementing

| Widget | Data source | Purpose |
|--------|-------------|---------|
| Campus pulse strip | `clarity.status`, drive-ready %, coverage, `upcoming_drives` | Green/amber/red at a glance |
| Today's priorities | `clarity.priorities`, `clarity.concerns` | What to do now (no AI click) |
| Needs attention | `at_risk`, `never_started`, `inactive_14d` | Who to follow up |
| Assessment funnel | `level_funnel` | 8-check progress campus-wide |
| Tool coverage bars | `tool_coverage` | Which check is stuck |
| Branch snapshot | `by_department` mini heatmap | Which branch leads/lags |

## Phase 2 — Performance deep dive ✅ implementing

| Widget | Data source | Purpose |
|--------|-------------|---------|
| Dept heatmap | `by_department.pillars` | Faster compare than grouped bars |
| Shortlist board | `area_boards[].top` | Who to send to drives |
| Hold list | `area_boards[].less_prepared` | Who needs more prep |
| Drive countdown banner | `upcoming_drives` + drive-ready % | Urgency before drive |
| Student filters | scorecards + `at_risk` ids | drive-ready / inactive / never / at-risk |
| Extra student columns | scorecards | best area, drive-ready badge |

## Phase 3 — Later (not this sprint)

- ~~Trend sparklines (needs historical API)~~ **Done** — `org_performance_snapshots` + `GET /performance/trends`
- ~~Export shortlist CSV~~ **Done** — frontend `ExportCsvButton`
- ~~Department detail page~~ **Done** — `/Organization/tpo/departments/:deptId`
- ~~Bulk notify inactive students~~ **Done** — `POST /performance/notify-cohort`

## Phase 3 — Remaining (future)

- Compare 2 branches side-by-side
- Scheduled weekly email digest to TPO
- Export PDF board pack for principal meetings

## Page layout

### TPO Dashboard
1. Campus pulse
2. Priorities + needs attention (2-col)
3. Funnel + tool coverage (2-col)
4. Branch heatmap snapshot
5. AI brief (collapsed / weekly)

### TPO Performance
1. Drive banner (if upcoming)
2. Stats + charts (existing + heatmap)
3. Shortlist / hold boards
4. Dept table + filtered student list
5. AI brief (single instance)
