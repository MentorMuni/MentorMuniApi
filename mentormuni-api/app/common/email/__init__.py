"""Common email package — send customized messages via SMTP."""

from app.common.email.exceptions import (
    EmailDeliveryError,
    EmailError,
    EmailNotConfiguredError,
)
from app.common.email.flows import send_tpo_activation_email
from app.common.email.sender import (
    is_email_configured,
    is_email_enabled,
    send_email,
    send_simple_email,
)
from app.common.email.types import EmailAddress, EmailSendResult, OutgoingEmail

__all__ = [
    "EmailAddress",
    "EmailDeliveryError",
    "EmailError",
    "EmailNotConfiguredError",
    "EmailSendResult",
    "OutgoingEmail",
    "is_email_configured",
    "is_email_enabled",
    "send_email",
    "send_simple_email",
    "send_tpo_activation_email",
]
