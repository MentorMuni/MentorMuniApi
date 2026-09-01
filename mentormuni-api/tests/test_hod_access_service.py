"""Tests for per-organization HOD access policy."""

from app.organizations.hod_access_service import (
    default_policy_dict,
    filter_permissions_for_hod,
)


def test_default_policy_allows_all_dept_admin_permissions():
    perms = frozenset(
        {
            "UPLOAD_STUDENTS",
            "APPROVE_STUDENT",
            "VIEW_REPORTS",
            "VIEW_DEPARTMENT_STUDENTS",
            "ASSIGN_PROGRAM",
            "SEND_NOTIFICATION",
            "ASSIGN_ASSESSMENT",
            "VIEW_SELF",
        }
    )
    filtered = filter_permissions_for_hod(perms, default_policy_dict())
    assert filtered == perms


def test_disable_invite_removes_student_invite_permissions():
    perms = frozenset({"UPLOAD_STUDENTS", "APPROVE_STUDENT", "VIEW_SELF"})
    policy = {**default_policy_dict(), "can_invite_students": False}
    filtered = filter_permissions_for_hod(perms, policy)
    assert filtered == frozenset({"VIEW_SELF"})


def test_disable_mocks_removes_assign_assessment_only():
    perms = frozenset({"ASSIGN_ASSESSMENT", "ASSIGN_PROGRAM", "VIEW_SELF"})
    policy = {**default_policy_dict(), "can_run_mocks": False}
    filtered = filter_permissions_for_hod(perms, policy)
    assert filtered == frozenset({"ASSIGN_PROGRAM", "VIEW_SELF"})


def test_disable_assign_programs_removes_program_permissions():
    perms = frozenset({"ASSIGN_PROGRAM", "CREATE_COMPETITION", "VIEW_SELF"})
    policy = {**default_policy_dict(), "can_assign_programs": False}
    filtered = filter_permissions_for_hod(perms, policy)
    assert filtered == frozenset({"VIEW_SELF"})
