"""Canonical fear chips shown in the student UI (and validated server-side)."""

from __future__ import annotations

from app.know_my_fear.schemas import FearCatalogItem, FearCatalogOut

FEAR_CATALOG: list[FearCatalogItem] = [
    FearCatalogItem(
        id="placement_fomo",
        label="Placement FOMO is eating me",
        blurb="Everyone else seems ahead; I feel late.",
        group="placement",
    ),
    FearCatalogItem(
        id="communication",
        label="I freeze when I speak",
        blurb="Bad communication — ideas stay stuck in my head.",
        group="communication",
    ),
    FearCatalogItem(
        id="english",
        label="My English isn't good enough",
        blurb="I worry HR / interviews will judge my English.",
        group="communication",
    ),
    FearCatalogItem(
        id="technical",
        label="My technical skills feel weak",
        blurb="DSA, core subjects, or stack confidence is shaky.",
        group="skills",
    ),
    FearCatalogItem(
        id="no_own_project",
        label="I never built a project myself",
        blurb="Tutorials yes — something of my own, no.",
        group="skills",
    ),
    FearCatalogItem(
        id="what_to_study",
        label="I don't know what to study",
        blurb="Too many topics; no clear path.",
        group="direction",
    ),
    FearCatalogItem(
        id="where_from",
        label="I don't know where to learn from",
        blurb="Courses, YouTube, notes — which ones actually help?",
        group="direction",
    ),
    FearCatalogItem(
        id="which_skills",
        label="I don't know which skills matter",
        blurb="Afraid of learning the wrong things.",
        group="direction",
    ),
    FearCatalogItem(
        id="aptitude",
        label="Aptitude will sink me",
        blurb="Quant / logical / verbal — not prepared.",
        group="rounds",
    ),
    FearCatalogItem(
        id="hr_fomo",
        label="HR round scares me",
        blurb="Tell me about yourself, gaps, salary talk…",
        group="rounds",
    ),
    FearCatalogItem(
        id="interview_fear",
        label="I'm terrified of interviews",
        blurb="Blank mind, shaking hands, overthinking.",
        group="rounds",
    ),
    FearCatalogItem(
        id="ask_for_help",
        label="I'm afraid to ask how to prepare",
        blurb="Asking seniors/friends feels embarrassing.",
        group="support",
    ),
    FearCatalogItem(
        id="family_pressure",
        label="Fear of home if I'm not placed",
        blurb="Family expectations feel heavy.",
        group="support",
    ),
    FearCatalogItem(
        id="friends_placed",
        label="What if my friends get placed and I don't",
        blurb="Comparison is loud and painful.",
        group="support",
    ),
    FearCatalogItem(
        id="plan_b",
        label="What if I'm not placed — then what?",
        blurb="Other options feel unclear or shameful.",
        group="support",
    ),
]

GROUP_LABELS = {
    "placement": "Placement pressure",
    "communication": "Speaking & English",
    "skills": "Skills & projects",
    "direction": "What / where / which",
    "rounds": "Aptitude · HR · interview",
    "support": "People & Plan B",
}

PRIVACY_NOTE = (
    "This page is private to you. Your TPO and HOD cannot see what you pick or write here. "
    "Feel free to open up — this is your space."
)


def catalog_out() -> FearCatalogOut:
    groups = [{"id": k, "label": v} for k, v in GROUP_LABELS.items()]
    return FearCatalogOut(privacy_note=PRIVACY_NOTE, groups=groups, fears=FEAR_CATALOG)


def resolve_fears(selections: list) -> list[dict]:
    by_id = {f.id: f for f in FEAR_CATALOG}
    out: list[dict] = []
    seen: set[str] = set()
    for sel in selections:
        fid = getattr(sel, "id", None) or (sel.get("id") if isinstance(sel, dict) else None)
        if not fid or fid in seen or fid not in by_id:
            continue
        seen.add(fid)
        inten = getattr(sel, "intensity", None)
        if inten is None and isinstance(sel, dict):
            inten = sel.get("intensity")
        item = by_id[fid]
        out.append(
            {
                "id": item.id,
                "label": item.label,
                "blurb": item.blurb,
                "group": item.group,
                "intensity": inten,
            }
        )
    return out
