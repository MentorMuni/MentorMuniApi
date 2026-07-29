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
from app.common.email.templates import render_tpo_activation_email
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
) -> EmailSendResult:
    """
    Send TPO activate / re-activate email.

    Does not raise on soft-skip (EMAIL_ENABLED=false).
    Delivery / config errors are logged and re-raised as EmailError subclasses
    so the caller can decide whether to fail the API or return a warning.
    """
    content = render_tpo_activation_email(
        first_name=first_name,
        last_name=last_name,
        username=username,
        organization_name=organization_name,
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
        logger.warning(
            "tpo_activation_email_failed to=%s reinvite=%s err=%s",
            to_email,
            is_reinvite,
            exc,
        )
        raise
