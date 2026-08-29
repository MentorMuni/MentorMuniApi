"""DNS-safe college portal slugs for *.mentormuni.com tenants."""

from __future__ import annotations

import re
from typing import Optional

from app.core.config import settings

RESERVED_PORTAL_SLUGS = frozenset(
    {
        "www",
        "app",
        "api",
        "admin",
        "platform",
        "mail",
        "ftp",
        "staging",
        "cdn",
        "static",
        "assets",
        "mentormuni",
        "public",
        "individual",
        "student",
        "students",
        "org",
        "organization",
        "tpo",
        "hod",
        "help",
        "status",
        "docs",
    }
)

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,30}[a-z0-9])?$")


def normalize_portal_slug(raw: str | None) -> str:
    """Lowercase, spaces→hyphens, strip non [a-z0-9-], collapse hyphens."""
    s = str(raw or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def validate_portal_slug(raw: str | None, *, required: bool = True) -> Optional[str]:
    """
    Return normalized slug or None if empty and not required.
    Raises ValueError on invalid / reserved.
    """
    if raw is None or not str(raw).strip():
        if required:
            raise ValueError("portal_slug is required.")
        return None
    slug = normalize_portal_slug(raw)
    if len(slug) < 3 or len(slug) > 32:
        raise ValueError("portal_slug must be 3–32 characters (letters, numbers, hyphens).")
    if not _SLUG_RE.match(slug):
        raise ValueError(
            "portal_slug must start and end with a letter or number "
            "(lowercase letters, digits, hyphens only)."
        )
    if slug in RESERVED_PORTAL_SLUGS:
        raise ValueError(f"portal_slug '{slug}' is reserved.")
    return slug


def apex_portal_base_url() -> str:
    return (settings.org_portal_base_url or "https://www.mentormuni.com").rstrip("/")


def college_portal_base_url(portal_slug: str | None) -> str:
    """
    https://{slug}.mentormuni.com when slug is set and apex is a mentormuni.com host;
    otherwise fall back to apex (local / custom FE bases).
    """
    apex = apex_portal_base_url()
    slug = normalize_portal_slug(portal_slug) if portal_slug else ""
    if not slug or slug in RESERVED_PORTAL_SLUGS:
        return apex
    # Local / custom bases keep path-style until wildcard DNS exists.
    if "mentormuni.com" not in apex.lower():
        return apex
    # Prefer apex scheme; strip www. for subdomain host.
    if apex.startswith("https://"):
        return f"https://{slug}.mentormuni.com"
    if apex.startswith("http://"):
        return f"http://{slug}.mentormuni.com"
    return f"https://{slug}.mentormuni.com"
