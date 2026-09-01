"""Unit tests for cross-portal login gates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.auth.service import AuthError, ensure_login_portal_allowed
from app.models.enums import RoleCode


def _user(*, role_code: str, org_code: str = "COLLEGE_A") -> SimpleNamespace:
    return SimpleNamespace(
        role=SimpleNamespace(role_code=role_code),
        organization=SimpleNamespace(code=org_code),
    )


def test_org_portal_rejects_student() -> None:
    user = _user(role_code=RoleCode.STUDENT.value)
    with pytest.raises(AuthError) as exc:
        ensure_login_portal_allowed(
            user, portal="organization", organization_code="COLLEGE_A"
        )
    assert exc.value.code == "WRONG_PORTAL"


def test_org_portal_requires_college_code() -> None:
    user = _user(role_code=RoleCode.ORG_ADMIN.value)
    with pytest.raises(AuthError) as exc:
        ensure_login_portal_allowed(user, portal="organization", organization_code="")
    assert exc.value.code == "ORGANIZATION_CODE_REQUIRED"


def test_org_portal_rejects_wrong_college_code() -> None:
    user = _user(role_code=RoleCode.ORG_ADMIN.value, org_code="COLLEGE_A")
    with pytest.raises(AuthError) as exc:
        ensure_login_portal_allowed(
            user, portal="organization", organization_code="COLLEGE_B"
        )
    assert exc.value.code == "WRONG_TENANT"


def test_org_portal_allows_matching_tpo() -> None:
    user = _user(role_code=RoleCode.ORG_ADMIN.value, org_code="COLLEGE_A")
    ensure_login_portal_allowed(
        user, portal="organization", organization_code="college_a"
    )


def test_student_portal_rejects_tpo() -> None:
    user = _user(role_code=RoleCode.ORG_ADMIN.value)
    with pytest.raises(AuthError) as exc:
        ensure_login_portal_allowed(user, portal="student", organization_code=None)
    assert exc.value.code == "WRONG_PORTAL"


def test_student_portal_allows_student() -> None:
    user = _user(role_code=RoleCode.STUDENT.value)
    ensure_login_portal_allowed(user, portal="student", organization_code=None)


def test_no_portal_skips_gate() -> None:
    user = _user(role_code=RoleCode.STUDENT.value)
    ensure_login_portal_allowed(user, portal=None, organization_code=None)
