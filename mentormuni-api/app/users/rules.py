"""
Backend rules for users.department_id.

Call `validate_department_for_role` in the users service BEFORE saving.

Rules:
  ORG_ADMIN              → department_id must be NULL
  DEPARTMENT_ADMIN       → department_id REQUIRED
  STUDENT + COLLEGE org  → department_id REQUIRED
  STUDENT + PUBLIC org   → department_id must be NULL
"""

from __future__ import annotations

from app.models.enums import OrganizationType, RoleCode


class UserRuleError(ValueError):
    """Raised when a user payload violates Phase 1 business rules."""


def validate_department_for_role(
    *,
    role_code: str,
    organization_type: str,
    department_id: int | None,
) -> None:
    """
    Raise UserRuleError if department_id does not match the role/org rules.

    Always pass role_code (string), never a hardcoded role id.
    """
    if role_code == RoleCode.ORG_ADMIN.value:
        if department_id is not None:
            raise UserRuleError("ORG_ADMIN must have department_id = NULL")
        return

    if role_code == RoleCode.DEPARTMENT_ADMIN.value:
        if department_id is None:
            raise UserRuleError("DEPARTMENT_ADMIN requires a department_id")
        return

    if role_code == RoleCode.STUDENT.value:
        if organization_type == OrganizationType.PUBLIC.value:
            if department_id is not None:
                raise UserRuleError(
                    "Individual (PUBLIC) STUDENT must have department_id = NULL"
                )
        elif organization_type == OrganizationType.COLLEGE.value:
            if department_id is None:
                raise UserRuleError("College STUDENT requires a department_id")
        else:
            raise UserRuleError(f"Unknown organization_type: {organization_type}")
        return

    raise UserRuleError(f"Unknown role_code: {role_code}")
