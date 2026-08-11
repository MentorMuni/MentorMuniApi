"""
Phase 1 enum values.

Stored as VARCHAR in Postgres (not native ENUM) so adding a new
value later is a simple app change — no ALTER TYPE migration needed.
"""

from __future__ import annotations

from enum import Enum


class OrganizationType(str, Enum):
    COLLEGE = "COLLEGE"
    PUBLIC = "PUBLIC"


class OrganizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class PlanType(str, Enum):
    COLLEGE = "COLLEGE"
    INDIVIDUAL = "INDIVIDUAL"


class PlanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class DepartmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class UserStatus(str, Enum):
    INVITED = "INVITED"  # TPO created; waiting to set password via activation link
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


class PlatformRole(str, Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    SUPPORT = "SUPPORT"
    SALES = "SALES"
    OPERATIONS = "OPERATIONS"


class PlatformUserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class FeatureCatalogStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RoleCode(str, Enum):
    """
    Always look up roles by role_code — never hardcode role IDs.
    """

    ORG_ADMIN = "ORG_ADMIN"
    DEPARTMENT_ADMIN = "DEPARTMENT_ADMIN"
    STUDENT = "STUDENT"


class OrgAdminTitle(str, Enum):
    """
    Display title for ORG_ADMIN users (same access, different label).

    Max one ACTIVE/INVITED of each title per organization.
    Primary contact for the org = TPO.
    """

    TPO = "TPO"
    DEAN = "DEAN"
    DIRECTOR = "DIRECTOR"


class DeptAdminTitle(str, Enum):
    """
    Display title for DEPARTMENT_ADMIN users (same access, different label).

    Max one ACTIVE/INVITED of each title per department.
    HOD is the primary mentor; Placement Coordinator is an optional peer.
    """

    HOD = "HOD"
    PLACEMENT_COORDINATOR = "PLACEMENT_COORDINATOR"


class NotificationAudience(str, Enum):
    ORG = "ORG"  # all active students in org (FE: all)
    DEPARTMENT = "DEPARTMENT"  # students in one department
    HODS = "HODS"  # live DEPARTMENT_ADMINs only
    USERS = "USERS"


class NotificationKind(str, Enum):
    EVENT = "event"
    WORKSHOP = "workshop"
    ANNOUNCEMENT = "announcement"


class NotificationDeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class NotificationRecipientStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"


class SupportTicketStatus(str, Enum):
    OPEN = "OPEN"
    WAITING_PLATFORM = "WAITING_PLATFORM"
    WAITING_REPORTER = "WAITING_REPORTER"
    CLOSED = "CLOSED"


class SupportSourcePortal(str, Enum):
    STUDENT = "student"
    ORGANIZATION = "organization"


class SupportCategory(str, Enum):
    NOT_WORKING = "not_working"
    FEATURE_BROKEN = "feature_broken"
    FEEDBACK = "feedback"
    OTHER = "other"
