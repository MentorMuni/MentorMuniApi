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
from app.models.feature_catalog import FeatureCatalog
from app.models.organization_feature import OrganizationFeature
from app.models.platform_user import PlatformUser

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
]
