"""
Organization access gates (ACTIVE vs SUSPENDED).

Uses the existing ``organizations.status`` column — no extra table.

Rules
-----
- COLLEGE + SUSPENDED → TPO / HOD / students cannot log in or use the org portal.
- New signups, approvals (via auth deps), dept creates, TPO activate/invite are blocked.
- Subscriptions remain in DB; platform can still manage the org (unsuspend, assign plan).
- PUBLIC (MentorMuni Public) must never be suspended — individuals stay unaffected.
- Platform portal logins (platform_users) are unaffected.
"""

from __future__ import annotations

from typing import Optional

from app.models.enums import OrganizationStatus, OrganizationType, RoleCode
from app.models.organization import Organization

# --- User-facing messages (API ``detail``; UI can show as-is) ---

MSG_STUDENT_ORG_SUSPENDED = (
    "Your organization's access has ended. Please contact your TPO."
)
MSG_STAFF_ORG_SUSPENDED = (
    "This organization is suspended. Contact MentorMuni support."
)
MSG_REGISTRATION_DISABLED = (
    "This organization is suspended. Registration is disabled."
)
MSG_ACTIVATION_DISABLED = (
    "This organization is suspended. Activation is disabled."
)
MSG_ORG_OPERATIONS_DISABLED = (
    "This organization is suspended. Contact MentorMuni support."
)
MSG_PUBLIC_CANNOT_SUSPEND = (
    "The PUBLIC (MentorMuni Public) organization cannot be suspended."
)


class OrganizationAccessError(Exception):
    """Raised when a suspended (or protected) organization blocks an action."""

    def __init__(self, message: str, *, status_code: int = 403) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def is_organization_suspended(organization: Organization) -> bool:
    return organization.status == OrganizationStatus.SUSPENDED.value


def is_public_organization(organization: Organization) -> bool:
    return (
        organization.code.upper() == "PUBLIC"
        or organization.organization_type == OrganizationType.PUBLIC.value
    )


def login_denied_message(*, role_code: Optional[str]) -> str:
    """Student-facing copy points them to TPO; staff contact MentorMuni."""
    if role_code == RoleCode.STUDENT.value:
        return MSG_STUDENT_ORG_SUSPENDED
    return MSG_STAFF_ORG_SUSPENDED


def ensure_organization_active_for_login(
    organization: Organization,
    *,
    role_code: Optional[str],
) -> None:
    """Block tenant login when the user's college is suspended."""
    if is_organization_suspended(organization):
        raise OrganizationAccessError(
            login_denied_message(role_code=role_code),
            status_code=403,
        )


def ensure_organization_active(
    organization: Organization,
    *,
    message: str = MSG_ORG_OPERATIONS_DISABLED,
) -> None:
    """Block tenant operations against a suspended organization."""
    if is_organization_suspended(organization):
        raise OrganizationAccessError(message, status_code=403)


def ensure_organization_accepts_registration(organization: Organization) -> None:
    ensure_organization_active(
        organization,
        message=MSG_REGISTRATION_DISABLED,
    )


def ensure_organization_accepts_activation(organization: Organization) -> None:
    ensure_organization_active(
        organization,
        message=MSG_ACTIVATION_DISABLED,
    )


def ensure_public_organization_not_suspended(
    organization: Organization,
    *,
    new_status: Optional[str] = None,
) -> None:
    """
    Refuse setting PUBLIC to SUSPENDED (create or update).

    Pass ``new_status`` when validating an incoming update payload.
    """
    target = new_status if new_status is not None else organization.status
    if is_public_organization(organization) and target == OrganizationStatus.SUSPENDED.value:
        raise OrganizationAccessError(MSG_PUBLIC_CANNOT_SUSPEND, status_code=400)
    # Creating a brand-new PUBLIC org already suspended
    if (
        new_status == OrganizationStatus.SUSPENDED.value
        and organization.organization_type == OrganizationType.PUBLIC.value
    ):
        raise OrganizationAccessError(MSG_PUBLIC_CANNOT_SUSPEND, status_code=400)


def reject_suspend_if_public(
    *,
    organization: Organization,
    incoming_status: Optional[str],
) -> None:
    """Call before applying an update that may change ``status``."""
    if incoming_status is None:
        return
    if is_public_organization(organization) and incoming_status == OrganizationStatus.SUSPENDED.value:
        raise OrganizationAccessError(MSG_PUBLIC_CANNOT_SUSPEND, status_code=400)


def reject_create_public_as_suspended(
    *,
    organization_type: str,
    status: Optional[str],
) -> None:
    if (
        organization_type == OrganizationType.PUBLIC.value
        and status == OrganizationStatus.SUSPENDED.value
    ):
        raise OrganizationAccessError(MSG_PUBLIC_CANNOT_SUSPEND, status_code=400)
