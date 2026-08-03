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


class NotificationAudience(str, Enum):
    ORG = "ORG"
    DEPARTMENT = "DEPARTMENT"
    USERS = "USERS"


class NotificationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class NotificationRecipientStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"
