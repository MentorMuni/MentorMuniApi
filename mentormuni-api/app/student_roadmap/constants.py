"""Week-1 baseline tool sequence and deep links."""

from __future__ import annotations

from typing import Any

WEEK1_NUMBER = 1

STEP_STATUS_LOCKED = "locked"
STEP_STATUS_CURRENT = "current"
STEP_STATUS_DONE = "done"

WEEK_STATUS_IN_PROGRESS = "in_progress"
WEEK_STATUS_DONE = "done"

PLAN_STATUS_GENERATING = "generating"
PLAN_STATUS_READY = "ready"
PLAN_STATUS_FAILED = "failed"
PLAN_STATUS_SUPERSEDED = "superseded"

PROMPT_VERSION = "placement_90day_v1"
PLACEMENT_90DAY_MODEL = "gpt-4.1"
MAX_TOKENS_PLACEMENT_90DAY = 8192
# A generating row older than this lost its worker (deploy/crash) — allow a retry.
PLAN_GENERATING_STALE_SECONDS = 300

PROGRESS_TOPICS_PROMPT_VERSION = "progress_topics_v1"
PROGRESS_TOPICS_MODEL = "gpt-4.1"
MAX_TOKENS_PROGRESS_TOPICS = 2500

DEFAULT_TARGET_COMPANIES = [
    "TCS",
    "Accenture",
    "Persistent",
    "Microsoft",
    "Infosys",
    "Capgemini",
]

WEEK1_STEPS: list[dict[str, Any]] = [
    {
        "tool_code": "5_sec",
        "order": 1,
        "title": "5-sec snap test",
        "minutes": 5,
        "href": "/studentportal/tools/5_sec?from=roadmap",
    },
    {
        "tool_code": "aptitude",
        "order": 2,
        "title": "Aptitude readiness",
        "minutes": 20,
        "href": "/studentportal/tools/aptitude?from=roadmap",
    },
    {
        "tool_code": "skill_readiness",
        "order": 3,
        "title": "Skill readiness",
        "minutes": 25,
        "href": "/studentportal/tools/skill_readiness?from=roadmap",
    },
    {
        "tool_code": "skill_mock",
        "order": 4,
        "title": "Skill AI mock interview",
        "minutes": 45,
        "href": "/studentportal/tools/skill_mock?from=roadmap",
    },
    {
        "tool_code": "project_mock",
        "order": 5,
        "title": "Project AI mock interview",
        "minutes": 45,
        "href": "/studentportal/tools/project_mock?from=roadmap",
    },
    {
        "tool_code": "interview_readiness",
        "order": 6,
        "title": "Interview readiness",
        "minutes": 25,
        "href": "/studentportal/tools/interview_readiness?from=roadmap",
    },
    {
        "tool_code": "interview_mock",
        "order": 7,
        "title": "Interview AI mock",
        "minutes": 45,
        "href": "/studentportal/tools/interview_mock?from=roadmap",
    },
    {
        "tool_code": "hr_mock",
        "order": 8,
        "title": "HR AI mock interview",
        "minutes": 30,
        "href": "/studentportal/tools/hr_mock?from=roadmap",
    },
]

TOOL_CODES = {s["tool_code"] for s in WEEK1_STEPS}
TOOL_META = {s["tool_code"]: s for s in WEEK1_STEPS}

MOCK_TOOL_CODES = {"skill_mock", "project_mock", "interview_mock", "hr_mock"}
