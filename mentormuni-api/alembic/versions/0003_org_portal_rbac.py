"""
Org Portal Phase 2: permissions RBAC + soft-delete + password-reset columns.

Revision ID: 0003_org_portal_rbac
Revises: 0002_platform_portal
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_org_portal_rbac"
down_revision: Union[str, None] = "0002_platform_portal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("CREATE_DEPARTMENT", "Create or update departments"),
    ("CREATE_HOD", "Invite or manage department admins (HOD)"),
    ("APPROVE_STUDENT", "Approve or reject student registrations"),
    ("VIEW_ALL_STUDENTS", "View all students in the organization"),
    ("VIEW_DEPARTMENT_STUDENTS", "View students in own department"),
    ("UPLOAD_STUDENTS", "Bulk import students via CSV"),
    ("MANAGE_USER_STATUS", "Block or change user status"),
    ("ASSIGN_PROGRAM", "Assign programs to students"),
    ("ASSIGN_ASSESSMENT", "Assign assessments to students"),
    ("CREATE_COMPETITION", "Create competitions"),
    ("SEND_NOTIFICATION", "Send notifications to students"),
    ("EXPORT_REPORT", "Export reports"),
    ("VIEW_REPORTS", "View analytics and reports dashboards"),
    ("TAKE_ASSESSMENT", "Take assessments and tools"),
    ("VIEW_SELF_DASHBOARD", "View own student dashboard"),
    ("VIEW_SELF", "View and update own profile"),
]

ORG_ADMIN_PERMS = [
    "CREATE_DEPARTMENT",
    "CREATE_HOD",
    "APPROVE_STUDENT",
    "VIEW_ALL_STUDENTS",
    "VIEW_DEPARTMENT_STUDENTS",
    "UPLOAD_STUDENTS",
    "MANAGE_USER_STATUS",
    "ASSIGN_PROGRAM",
    "ASSIGN_ASSESSMENT",
    "CREATE_COMPETITION",
    "SEND_NOTIFICATION",
    "EXPORT_REPORT",
    "VIEW_REPORTS",
    "VIEW_SELF",
]

DEPT_ADMIN_PERMS = [
    "APPROVE_STUDENT",
    "VIEW_DEPARTMENT_STUDENTS",
    "UPLOAD_STUDENTS",
    "ASSIGN_PROGRAM",
    "ASSIGN_ASSESSMENT",
    "CREATE_COMPETITION",
    "SEND_NOTIFICATION",
    "EXPORT_REPORT",
    "VIEW_REPORTS",
    "VIEW_SELF",
]

STUDENT_PERMS = [
    "TAKE_ASSESSMENT",
    "VIEW_SELF_DASHBOARD",
    "VIEW_SELF",
]


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("permission_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("permission_code"),
    )
    op.create_index("ix_permissions_permission_code", "permissions", ["permission_code"])

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_perm"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.add_column("departments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("password_reset_token_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    conn = op.get_bind()
    for code, desc in PERMISSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (permission_code, description) VALUES (:c, :d)"
            ),
            {"c": code, "d": desc},
        )

    def _seed_role_safe(role_code: str, perm_codes: list[str]) -> None:
        role_id = conn.execute(
            sa.text("SELECT id FROM roles WHERE role_code = :r"), {"r": role_code}
        ).scalar()
        if role_id is None:
            return
        for pc in perm_codes:
            pid = conn.execute(
                sa.text("SELECT id FROM permissions WHERE permission_code = :p"),
                {"p": pc},
            ).scalar()
            if pid is None:
                continue
            exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"
                ),
                {"rid": role_id, "pid": pid},
            ).scalar()
            if not exists:
                conn.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"
                    ),
                    {"rid": role_id, "pid": pid},
                )

    _seed_role_safe("ORG_ADMIN", ORG_ADMIN_PERMS)
    _seed_role_safe("DEPARTMENT_ADMIN", DEPT_ADMIN_PERMS)
    _seed_role_safe("STUDENT", STUDENT_PERMS)


def downgrade() -> None:
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "deleted_at")
    op.drop_column("departments", "deleted_at")
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_permission_code", table_name="permissions")
    op.drop_table("permissions")
