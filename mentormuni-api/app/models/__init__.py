"""
ORM models package.

Import this package so Alembic and the app register every model:

    import app.models  # noqa: F401
"""

from app.models.organization import Organization
from app.models.subscription_plan import SubscriptionPlan
from app.models.organization_subscription import OrganizationSubscription
from app.models.role import Role
from app.models.department import Department
from app.models.user import User
from app.models.private_checkin import (
    PrivateStudentCheckIn,
    PrivateStudentResponse,
    PrivateStudentInsight,
    PrivateStudentProgress,
)
from app.models.private_intervention import (
    PrivateStudentFearSolution,
    PrivateStudentWeeklyProgress,
    PrivateStudentWeeklyCheckin,
    PrivateStudentNotification,
    PrivateStudentMilestone,
    PrivateStudentInterventionStats,
    PrivateStudentPlanAction,
)
from app.models.feature_catalog import FeatureCatalog
from app.models.organization_feature import OrganizationFeature
from app.models.platform_user import PlatformUser
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.notification_recipient import NotificationRecipient
from app.models.workspace_item import WorkspaceItem
from app.models.upcoming_drive import UpcomingDrive
from app.models.platform_support import PlatformSupportTicket, PlatformSupportReply
from app.models.whiteboard import WhiteboardMentorship, WhiteboardNote
from app.org_performance.models import OrgPerformanceSnapshot
from app.student_roadmap.models import (
    StudentAssessmentResult,
    StudentGeneratedRoadmap,
    StudentRoadmapStep,
    StudentRoadmapWeek,
)
from app.student_intelligence.models import (
    StudentAttempt,
    StudentCoverageLedger,
    StudentDailyActivity,
    StudentDailyTaskLedger,
    StudentMemoryFact,
    StudentMissionAnchor,
    StudentReadinessSnapshot,
    StudentTarget,
    StudentTopicMastery,
)
from app.company_intelligence.models import CompanyIntelligence
from app.coding.models import (
    CodingAiAnalysis,
    CodingAssessment,
    CodingAssessmentProblem,
    CodingAttempt,
    CodingAttemptProblem,
    CodingAttemptSnapshot,
    CodingDraft,
    CodingGenerationRun,
    CodingJob,
    CodingLanguage,
    CodingProblem,
    CodingProblemRelevance,
    CodingProblemVersion,
    CodingReferenceSolution,
    CodingRun,
    CodingSubmission,
    CodingTestCase,
    CodingTestResult,
    CodingValidationResult,
)

__all__ = [
    "Organization",
    "SubscriptionPlan",
    "OrganizationSubscription",
    "Role",
    "Department",
    "User",
    "FeatureCatalog",
    "OrganizationFeature",
    "PlatformUser",
    "Permission",
    "RolePermission",
    "AuditLog",
    "Notification",
    "NotificationRecipient",
    "WorkspaceItem",
    "UpcomingDrive",
    "PlatformSupportTicket",
    "PlatformSupportReply",
    "WhiteboardNote",
    "WhiteboardMentorship",
    "StudentRoadmapWeek",
    "StudentRoadmapStep",
    "StudentAssessmentResult",
    "StudentGeneratedRoadmap",
    "OrgPerformanceSnapshot",
    "CompanyIntelligence",
    "PrivateStudentCheckIn",
    "PrivateStudentResponse",
    "PrivateStudentInsight",
    "PrivateStudentProgress",
    "PrivateStudentFearSolution",
    "PrivateStudentWeeklyProgress",
    "PrivateStudentWeeklyCheckin",
    "PrivateStudentNotification",
    "PrivateStudentMilestone",
    "PrivateStudentInterventionStats",
    "PrivateStudentPlanAction",
    "CodingLanguage",
    "CodingProblem",
    "CodingProblemVersion",
    "CodingReferenceSolution",
    "CodingTestCase",
    "CodingAssessment",
    "CodingAssessmentProblem",
    "CodingAttempt",
    "CodingAttemptSnapshot",
    "CodingAttemptProblem",
    "CodingDraft",
    "CodingRun",
    "CodingSubmission",
    "CodingTestResult",
    "CodingAiAnalysis",
    "CodingJob",
    "CodingProblemRelevance",
    "CodingGenerationRun",
    "CodingValidationResult",
]
