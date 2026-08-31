"""Ensure DEPARTMENT_ADMIN (HOD) has SEND_NOTIFICATION for campus notify."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0033_hod_send_notification"
down_revision: Union[str, None] = "0032_performance_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    role_id = conn.execute(
        sa.text("SELECT id FROM roles WHERE role_code = 'DEPARTMENT_ADMIN'")
    ).scalar()
    perm_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE permission_code = 'SEND_NOTIFICATION'")
    ).scalar()
    if role_id is None or perm_id is None:
        return
    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"
        ),
        {"rid": role_id, "pid": perm_id},
    ).scalar()
    if not exists:
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"
            ),
            {"rid": role_id, "pid": perm_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    role_id = conn.execute(
        sa.text("SELECT id FROM roles WHERE role_code = 'DEPARTMENT_ADMIN'")
    ).scalar()
    perm_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE permission_code = 'SEND_NOTIFICATION'")
    ).scalar()
    if role_id is None or perm_id is None:
        return
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"
        ),
        {"rid": role_id, "pid": perm_id},
    )
