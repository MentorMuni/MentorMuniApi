"""Alembic migration for private check-in tables."""
from alembic import op
import sqlalchemy as sa

revision = '0020_private_student_checkins'
down_revision = '0019_coding_question_bank'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PrivateStudentCheckIn
    op.create_table(
        'private_student_checkins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_psc_student_id_created',
        'private_student_checkins',
        ['student_id', 'created_at'],
    )

    # PrivateStudentResponse
    op.create_table(
        'private_student_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('question_key', sa.String(128), nullable=False),
        sa.Column('response_type', sa.String(32), nullable=False),
        sa.Column('response_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['checkin_id'], ['private_student_checkins.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_psr_checkin_id', 'private_student_responses', ['checkin_id'])

    # PrivateStudentInsight
    op.create_table(
        'private_student_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(32), nullable=False, server_default='openai'),
        sa.Column('model', sa.String(64), nullable=True),
        sa.Column('headline', sa.Text(), nullable=False),
        sa.Column('what_i_hear', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('blockers', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('action_plan', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('full_insight_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['checkin_id'], ['private_student_checkins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_psi_student_id_created',
        'private_student_insights',
        ['student_id', 'created_at'],
    )

    # PrivateStudentProgress (optional)
    op.create_table(
        'private_student_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('metric_key', sa.String(64), nullable=False),
        sa.Column('value_before', sa.Integer(), nullable=True),
        sa.Column('value_after', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['checkin_id'], ['private_student_checkins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_psp_student_id_created',
        'private_student_progress',
        ['student_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_psp_student_id_created', table_name='private_student_progress')
    op.drop_table('private_student_progress')

    op.drop_index('ix_psi_student_id_created', table_name='private_student_insights')
    op.drop_table('private_student_insights')

    op.drop_index('ix_psr_checkin_id', table_name='private_student_responses')
    op.drop_table('private_student_responses')

    op.drop_index('ix_psc_student_id_created', table_name='private_student_checkins')
    op.drop_table('private_student_checkins')
