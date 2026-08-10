"""SQLAlchemy models for Know Me intervention & fear resolution system."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database.base import Base
from app.know_my_fear.timeutil import utc_now


class PrivateStudentFearSolution(Base):
    """
    Store complete fear solution plans for each identified fear.
    Each fear gets a 6-week action plan with weekly breakdowns.
    """

    __tablename__ = "private_student_fear_solutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkin_id: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fear_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fear_name: Mapped[str] = mapped_column(String(256), nullable=False)
    fear_severity: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10

    # Complete solution plan in JSON
    # {
    #   "root_cause": "...",
    #   "week1": {"day1": "...", "day2": "..."},
    #   "week2": {...},
    #   ...
    #   "success_metrics": "..."
    # }
    solution_plan: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Weekly targets for tracking
    # ["Record 3 videos", "Get friend feedback", "Refine explanation"]
    weekly_actions: Mapped[list] = mapped_column(JSON, nullable=False)

    # Resources needed
    # ["Project explanation template", "Mock interview questions", "Mentor feedback form"]
    resources: Mapped[list] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class PrivateStudentWeeklyProgress(Base):
    """
    Track student progress against each fear solution.
    Weekly snapshots show fear severity reduction over time.
    """

    __tablename__ = "private_student_weekly_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fear_id: Mapped[str] = mapped_column(String(128), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-6

    # How many actions completed this week
    actions_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    actions_total: Mapped[int] = mapped_column(Integer, nullable=False)

    # Student's self-reported improvement (0-10)
    self_reported_improvement: Mapped[float] = mapped_column(Float, nullable=False)

    # AI-generated personalized feedback
    ai_feedback: Mapped[str] = mapped_column(Text, nullable=False)

    # Fear severity before/after this week
    severity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    severity_after: Mapped[int] = mapped_column(Integer, nullable=False)

    # What the student did this week
    # {"recorded_self": 3, "got_feedback": true, "practiced": 5}
    actions_summary: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Challenges encountered
    challenges: Mapped[str] = mapped_column(Text, nullable=True)

    # Next week's commitment from student
    next_week_commitment: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )


class PrivateStudentWeeklyCheckin(Base):
    """
    Student's weekly check-in responses.
    Simpler than full check-in, just tracks progress on specific fear.
    """

    __tablename__ = "private_student_weekly_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fear_id: Mapped[str] = mapped_column(String(128), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Which actions were completed
    # {"action1": true, "action2": false, "action3": true}
    actions_done: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Self-assessment on improvement (0-10)
    self_assessment: Mapped[float] = mapped_column(Float, nullable=False)

    # Any challenges they faced
    challenges: Mapped[str] = mapped_column(Text, nullable=True)

    # What they commit to next week
    next_week_commitment: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )


class PrivateStudentNotification(Base):
    """
    Track all notifications sent to student for Know Me journey.
    Used to measure engagement and re-send if needed.
    """

    __tablename__ = "private_student_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    checkin_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Type of notification
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # "start_week_1", "mid_week_check", "weekly_review", "milestone", "next_week_preview"

    # When it should be sent
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # When it was actually sent
    sent_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Did the student click on it?
    clicked: Mapped[bool] = mapped_column(Boolean, default=False)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Student's response (if applicable)
    # {"improvement_score": 7, "actions_completed": 3}
    response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # The actual notification content sent
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    cta_text: Mapped[str] = mapped_column(String(64), nullable=False)  # "View Plan", etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )


class PrivateStudentMilestone(Base):
    """
    Track milestone achievements in the 6-week journey.
    Used for celebrations and motivation tracking.
    """

    __tablename__ = "private_student_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fear_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # Type of milestone
    milestone_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # "fear_reduced_to_50", "week_1_complete", "fear_conquered", "all_fears_gone"

    # Week when milestone was achieved
    achieved_week: Mapped[int] = mapped_column(Integer, nullable=False)

    # Severity reduced to what level
    severity_reduced_to: Mapped[int] = mapped_column(Integer, nullable=True)

    # Celebration message shown to student
    celebration_message: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional data
    # {"previous_severity": 8, "current_severity": 4, "weeks_to_achieve": 2}
    # Note: cannot name this "metadata" — reserved by SQLAlchemy Declarative API
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    achieved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )


class PrivateStudentInterventionStats(Base):
    """
    Summary statistics for each student's complete intervention journey.
    Used for final celebration and performance metrics.
    """

    __tablename__ = "private_student_intervention_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    checkin_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Total stats across all fears
    total_fears: Mapped[int] = mapped_column(Integer, nullable=False)
    fears_conquered: Mapped[int] = mapped_column(Integer, nullable=False)

    # Time invested
    total_actions_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    total_actions_target: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    # Improvement metrics
    average_improvement_per_week: Mapped[float] = mapped_column(Float, nullable=False)
    total_fear_reduction: Mapped[int] = mapped_column(Integer, nullable=False)

    # Engagement metrics
    notifications_sent: Mapped[int] = mapped_column(Integer, nullable=False)
    notifications_clicked: Mapped[int] = mapped_column(Integer, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    # Time tracking
    days_to_zero_fear: Mapped[int] = mapped_column(Integer, nullable=True)

    # Final message
    final_celebration: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
