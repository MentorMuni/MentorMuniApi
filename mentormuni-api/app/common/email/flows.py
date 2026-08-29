"""Helpers that send product emails using the common sender + templates."""

from __future__ import annotations

import logging
from datetime import datetime

from app.common.email.exceptions import (
    EmailDeliveryError,
    EmailError,
    EmailNotConfiguredError,
)
from app.common.email.sender import send_email
from app.common.email.templates import (
    render_password_reset_email,
    render_staff_activation_email,
    render_individual_activation_email,
    render_student_activation_email,
    render_student_enrollment_denied_email,
    render_tpo_activation_email,
)
from app.common.email.types import EmailAddress, EmailSendResult, OutgoingEmail

logger = logging.getLogger(__name__)


async def send_tpo_activation_email(
    *,
    to_email: str,
    first_name: str,
    last_name: str,
    username: str,
    organization_name: str,
    raw_token: str,
    expires_at: datetime,
    is_reinvite: bool = False,
    role_label: str = "Org Admin",
    portal_slug: str | None = None,
) -> EmailSendResult:
    content = render_tpo_activation_email(
        first_name=first_name,
        last_name=last_name,
        username=username,
        organization_name=organization_name,
        raw_token=raw_token,
        expires_at=expires_at,
        is_reinvite=is_reinvite,
        role_label=role_label,
        portal_slug=portal_slug,
    )
    try:
        return await send_email(
            OutgoingEmail(
                to=[
                    EmailAddress(
                        email=to_email,
                        name=f"{first_name} {last_name}".strip() or None,
                    )
                ],
                subject=content.subject,
                text_body=content.text_body,
                html_body=content.html_body,
            )
        )
    except (EmailNotConfiguredError, EmailDeliveryError, EmailError) as exc:
        logger.warning(
            "tpo_activation_email_failed to=%s reinvite=%s err=%s",
            to_email,
            is_reinvite,
            exc,
        )
        raise


async def send_staff_activation_email(
    *,
    to_email: str,
    first_name: str,
    last_name: str,
    username: str,
    organization_name: str,
    role_label: str,
    raw_token: str,
    expires_at: datetime,
    is_reinvite: bool = False,
    portal_slug: str | None = None,
) -> EmailSendResult:
    content = render_staff_activation_email(
        first_name=first_name,
        last_name=last_name,
        username=username,
        organization_name=organization_name,
        role_label=role_label,
        raw_token=raw_token,
        expires_at=expires_at,
        is_reinvite=is_reinvite,
        portal_slug=portal_slug,
    )
    try:
        return await send_email(
            OutgoingEmail(
                to=[
                    EmailAddress(
                        email=to_email,
                        name=f"{first_name} {last_name}".strip() or None,
                    )
                ],
                subject=content.subject,
                text_body=content.text_body,
                html_body=content.html_body,
            )
        )
    except (EmailNotConfiguredError, EmailDeliveryError, EmailError) as exc:
        logger.warning(
            "staff_activation_email_failed to=%s role=%s err=%s",
            to_email,
            role_label,
            exc,
        )
        raise


async def send_student_activation_email(
    *,
    to_email: str,
    first_name: str,
    last_name: str,
    username: str,
    organization_name: str,
    department_name: str | None,
    raw_token: str,
    expires_at: datetime,
    portal_slug: str | None = None,
) -> EmailSendResult:
    content = render_student_activation_email(
        first_name=first_name,
        last_name=last_name,
        username=username,
        organization_name=organization_name,
        department_name=department_name,
        raw_token=raw_token,
        expires_at=expires_at,
        portal_slug=portal_slug,
    )
    try:
        return await send_email(
            OutgoingEmail(
                to=[
                    EmailAddress(
                        email=to_email,
                        name=f"{first_name} {last_name}".strip() or None,
                    )
                ],
                subject=content.subject,
                text_body=content.text_body,
                html_body=content.html_body,
            )
        )
    except (EmailNotConfiguredError, EmailDeliveryError, EmailError) as exc:
        logger.warning("student_activation_email_failed to=%s err=%s", to_email, exc)
        raise


async def send_individual_activation_email(
    *,
    to_email: str,
    first_name: str,
    last_name: str,
    username: str,
    raw_token: str,
    expires_at: datetime,
    is_reinvite: bool = False,
) -> EmailSendResult:
    content = render_individual_activation_email(
        first_name=first_name,
        last_name=last_name,
        username=username,
        raw_token=raw_token,
        expires_at=expires_at,
        is_reinvite=is_reinvite,
    )
    try:
        return await send_email(
            OutgoingEmail(
                to=[
                    EmailAddress(
                        email=to_email,
                        name=f"{first_name} {last_name}".strip() or None,
                    )
                ],
                subject=content.subject,
                text_body=content.text_body,
                html_body=content.html_body,
            )
        )
    except (EmailNotConfiguredError, EmailDeliveryError, EmailError) as exc:
        logger.warning("individual_activation_email_failed to=%s err=%s", to_email, exc)
        raise


async def send_student_enrollment_denied_email(
    *,
    to_email: str,
    first_name: str,
    last_name: str,
    organization_name: str,
    department_name: str | None,
) -> EmailSendResult:
    content = render_student_enrollment_denied_email(
        first_name=first_name,
        last_name=last_name,
        organization_name=organization_name,
        department_name=department_name,
    )
    try:
        return await send_email(
            OutgoingEmail(
                to=[
                    EmailAddress(
                        email=to_email,
                        name=f"{first_name} {last_name}".strip() or None,
                    )
                ],
                subject=content.subject,
                text_body=content.text_body,
                html_body=content.html_body,
            )
        )
    except (EmailNotConfiguredError, EmailDeliveryError, EmailError) as exc:
        logger.warning(
            "student_enrollment_denied_email_failed to=%s err=%s",
            to_email,
            exc,
        )
        raise


async def send_password_reset_email(
    *,
    to_email: str,
    first_name: str,
    last_name: str,
    organization_name: str,
    raw_token: str,
    expires_at: datetime,
    reset_path: str | None = None,
    portal_slug: str | None = None,
) -> EmailSendResult:
    content = render_password_reset_email(
        first_name=first_name,
        last_name=last_name,
        organization_name=organization_name,
        raw_token=raw_token,
        expires_at=expires_at,
        reset_path=reset_path,
        portal_slug=portal_slug,
    )
    try:
        return await send_email(
            OutgoingEmail(
                to=[
                    EmailAddress(
                        email=to_email,
                        name=f"{first_name} {last_name}".strip() or None,
                    )
                ],
                subject=content.subject,
                text_body=content.text_body,
                html_body=content.html_body,
            )
        )
    except (EmailNotConfiguredError, EmailDeliveryError, EmailError) as exc:
        logger.warning("password_reset_email_failed to=%s err=%s", to_email, exc)
        raise
