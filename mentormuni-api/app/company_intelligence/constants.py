"""Company Intelligence — shared hiring process data (not student-personalized)."""

from __future__ import annotations

STATUS_GENERATING = "generating"
STATUS_READY = "ready"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"

PROMPT_VERSION = "company_intelligence_v2"
COMPANY_INTEL_MODEL = "gpt-4.1"
MAX_TOKENS_COMPANY_INTEL = 6000
GENERATING_STALE_SECONDS = 300

DEFAULT_ROLE = "Software Engineer"
DEFAULT_COUNTRY = "India"

# Browse catalog — students can open these without searching first.
CURATED_COMPANIES: list[dict[str, str]] = [
    {"company": "TCS", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Infosys", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Accenture", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Wipro", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Cognizant", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Capgemini", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Persistent Systems", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Microsoft", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Amazon", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Google", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "IBM", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
    {"company": "Deloitte", "role": DEFAULT_ROLE, "country": DEFAULT_COUNTRY},
]
