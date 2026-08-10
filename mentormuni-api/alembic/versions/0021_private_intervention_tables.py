"""Create private intervention tables for 6-week fear resolution system.

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0021_private_intervention_tables'
down_revision = '0020_private_student_checkins'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create private intervention tables."""
    
    # private_student_fear_solutions
    op.create_table(
        'private_student_fear_solutions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('fear_id', sa.String(128), nullable=False),
        sa.Column('fear_name', sa.String(256), nullable=False),
        sa.Column('fear_severity', sa.Integer(), nullable=False),
        sa.Column('solution_plan', postgresql.JSON(), nullable=False),
        sa.Column('weekly_actions', postgresql.JSON(), nullable=False),
        sa.Column('resources', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_private_fear_solutions_student', 'private_student_fear_solutions', ['student_id', 'created_at'])
    op.create_index('idx_private_fear_solutions_checkin', 'private_student_fear_solutions', ['checkin_id'])
    
    # private_student_weekly_progress
    op.create_table(
        'private_student_weekly_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('fear_id', sa.String(128), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('actions_completed', sa.Integer(), nullable=False),
        sa.Column('actions_total', sa.Integer(), nullable=False),
        sa.Column('self_reported_improvement', sa.Float(), nullable=False),
        sa.Column('ai_feedback', sa.Text(), nullable=False),
        sa.Column('severity_before', sa.Integer(), nullable=False),
        sa.Column('severity_after', sa.Integer(), nullable=False),
        sa.Column('actions_summary', postgresql.JSON(), nullable=True),
        sa.Column('challenges', sa.Text(), nullable=True),
        sa.Column('next_week_commitment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_private_weekly_progress_student', 'private_student_weekly_progress', ['student_id', 'fear_id', 'week_number'])
    
    # private_student_weekly_checkins
    op.create_table(
        'private_student_weekly_checkins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('fear_id', sa.String(128), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('actions_done', postgresql.JSON(), nullable=False),
        sa.Column('self_assessment', sa.Float(), nullable=False),
        sa.Column('challenges', sa.Text(), nullable=True),
        sa.Column('next_week_commitment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_private_checkins_student', 'private_student_weekly_checkins', ['student_id', 'fear_id'])
    
    # private_student_notifications
    op.create_table(
        'private_student_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(64), nullable=False),
        sa.Column('scheduled_date', sa.DateTime(), nullable=False),
        sa.Column('sent_date', sa.DateTime(), nullable=True),
        sa.Column('clicked', sa.Boolean(), default=False),
        sa.Column('clicked_at', sa.DateTime(), nullable=True),
        sa.Column('response', postgresql.JSON(), nullable=True),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('cta_text', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_private_notifications_student', 'private_student_notifications', ['student_id', 'scheduled_date'])
    op.create_index('idx_private_notifications_type', 'private_student_notifications', ['notification_type'])
    
    # private_student_milestones
    op.create_table(
        'private_student_milestones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('fear_id', sa.String(128), nullable=False),
        sa.Column('milestone_type', sa.String(64), nullable=False),
        sa.Column('achieved_week', sa.Integer(), nullable=False),
        sa.Column('severity_reduced_to', sa.Integer(), nullable=True),
        sa.Column('celebration_message', sa.Text(), nullable=False),
        sa.Column('extra_data', postgresql.JSON(), nullable=True),
        sa.Column('achieved_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_private_milestones_student', 'private_student_milestones', ['student_id', 'fear_id'])
    
    # private_student_intervention_stats
    op.create_table(
        'private_student_intervention_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('total_fears', sa.Integer(), nullable=False),
        sa.Column('fears_conquered', sa.Integer(), nullable=False),
        sa.Column('total_actions_completed', sa.Integer(), nullable=False),
        sa.Column('total_actions_target', sa.Integer(), nullable=False),
        sa.Column('completion_rate', sa.Float(), nullable=False),
        sa.Column('average_improvement_per_week', sa.Float(), nullable=False),
        sa.Column('total_fear_reduction', sa.Integer(), nullable=False),
        sa.Column('notifications_sent', sa.Integer(), nullable=False),
        sa.Column('notifications_clicked', sa.Integer(), nullable=False),
        sa.Column('engagement_rate', sa.Float(), nullable=False),
        sa.Column('days_to_zero_fear', sa.Integer(), nullable=True),
        sa.Column('final_celebration', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_private_stats_student', 'private_student_intervention_stats', ['student_id', 'checkin_id'])


def downgrade() -> None:
    """Drop private intervention tables."""
    
    op.drop_index('idx_private_stats_student', table_name='private_student_intervention_stats')
    op.drop_table('private_student_intervention_stats')
    
    op.drop_index('idx_private_milestones_student', table_name='private_student_milestones')
    op.drop_table('private_student_milestones')
    
    op.drop_index('idx_private_notifications_type', table_name='private_student_notifications')
    op.drop_index('idx_private_notifications_student', table_name='private_student_notifications')
    op.drop_table('private_student_notifications')
    
    op.drop_index('idx_private_checkins_student', table_name='private_student_weekly_checkins')
    op.drop_table('private_student_weekly_checkins')
    
    op.drop_index('idx_private_weekly_progress_student', table_name='private_student_weekly_progress')
    op.drop_table('private_student_weekly_progress')
    
    op.drop_index('idx_private_fear_solutions_checkin', table_name='private_student_fear_solutions')
    op.drop_index('idx_private_fear_solutions_student', table_name='private_student_fear_solutions')
    op.drop_table('private_student_fear_solutions')
