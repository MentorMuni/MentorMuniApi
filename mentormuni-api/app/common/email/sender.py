"""
Async SMTP email sender — shared by all product flows.

Usage::

    from app.common.email import EmailAddress, OutgoingEmail, send_email

    result = await send_email(
        OutgoingEmail(
            to=[EmailAddress(email="tpo@college.edu", name="Priya")],
            subject="Activate your MentorMuni account",
            text_body="...",
            html_body="<p>...</p>",
        )
    )

Configure via env (see Settings / .env.example). When ``EMAIL_ENABLED=false``,
``send_email`` returns ``skipped=True`` and does not raise — callers stay safe
in local/dev without SMTP.

Railway note: outbound SMTP to ``smtp.gmail.com:587`` often times out.
Prefer ``SMTP_PORT=465`` + ``SMTP_USE_SSL=true``, or rely on the automatic
587 → 465 fallback in ``send_email``.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Optional

import aiosmtplib

from app.common.email.exceptions import (
    EmailDeliveryError,
    EmailError,
    EmailNotConfiguredError,
)
from app.common.email.types import EmailAddress, EmailSendResult, OutgoingEmail
from app.core.config import settings

logger = logging.getLogger(__name__)


def is_email_enabled() -> bool:
    return bool(settings.email_enabled)


def is_email_configured() -> bool:
    """True when we can attempt SMTP (enabled + from + password)."""
    return bool(
        settings.email_enabled
        and settings.smtp_host
        and settings.email_from_address
        and settings.smtp_password
    )


def _default_from_address() -> EmailAddress:
    return EmailAddress(
        email=settings.email_from_address,
        name=settings.email_from_name or None,
    )


def _format_address(addr: EmailAddress) -> str:
    if addr.name and addr.name.strip():
        return formataddr((addr.name.strip(), addr.email.strip()))
    return addr.email.strip()


def _build_mime_message(payload: OutgoingEmail) -> EmailMessage:
    sender = payload.from_address or _default_from_address()
    if not sender.email:
        raise EmailNotConfiguredError("EMAIL_FROM_ADDRESS is not set.")

    msg = EmailMessage()
    msg["Subject"] = payload.subject.strip()
    msg["From"] = _format_address(sender)
    msg["To"] = ", ".join(_format_address(a) for a in payload.to)
    if payload.cc:
        msg["Cc"] = ", ".join(_format_address(a) for a in payload.cc)
    reply = payload.reply_to
    if reply is None and settings.email_reply_to:
        reply = EmailAddress(email=settings.email_reply_to)
    if reply is not None:
        msg["Reply-To"] = _format_address(reply)

    message_id = make_msgid(domain=sender.email.split("@")[-1] if "@" in sender.email else None)
    msg["Message-ID"] = message_id

    text = payload.text_body
    html = payload.html_body
    if text and html:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    elif html:
        msg.set_content("This email requires an HTML-capable client.")
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(text or "")

    return msg


def _all_envelope_recipients(payload: OutgoingEmail) -> list[str]:
    addrs: list[str] = []
    for group in (payload.to, payload.cc, payload.bcc):
        for item in group:
            addrs.append(item.email.strip())
    # Preserve order, drop dupes
    seen: set[str] = set()
    unique: list[str] = []
    for a in addrs:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def _is_connect_timeout(exc: BaseException) -> bool:
    text = str(exc).lower()
    if "timed out" in text or "timeout" in text:
        return True
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, OSError, ConnectionError)):
        return True
    # aiosmtplib wraps some connect failures
    name = type(exc).__name__.lower()
    return "timeout" in name


def _smtp_attempts() -> list[tuple[int, bool, bool]]:
    """
    Ordered (port, start_tls, use_ssl) attempts.

    Primary = Settings. Then Gmail-friendly alternate if host is Gmail and
    primary looks like the flaky Railway :587 STARTTLS path.
    """
    primary_start_tls = settings.smtp_use_tls and not settings.smtp_use_ssl
    primary = (settings.smtp_port, primary_start_tls, bool(settings.smtp_use_ssl))
    attempts = [primary]

    host = (settings.smtp_host or "").lower()
    if "gmail.com" in host or "google.com" in host:
        # Railway often cannot open smtp.gmail.com:587 — SSL 465 usually works.
        alt = (465, False, True)
        if alt != primary:
            attempts.append(alt)
        # Also try 587 STARTTLS if primary was 465
        alt587 = (587, True, False)
        if alt587 != primary and alt587 not in attempts:
            attempts.append(alt587)

    return attempts


async def _smtp_send_once(
    mime: EmailMessage,
    *,
    recipients: list[str],
    port: int,
    start_tls: bool,
    use_ssl: bool,
) -> None:
    tls_context = ssl.create_default_context() if (start_tls or use_ssl) else None
    await aiosmtplib.send(
        mime,
        hostname=settings.smtp_host,
        port=port,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        start_tls=start_tls,
        use_tls=use_ssl,
        tls_context=tls_context,
        recipients=recipients,
        timeout=settings.smtp_timeout_seconds,
    )


async def send_email(
    payload: OutgoingEmail,
    *,
    raise_on_skip: bool = False,
) -> EmailSendResult:
    """
    Send a customized email via SMTP.

    Parameters
    ----------
    payload:
        Recipients + subject + body (caller-owned content).
    raise_on_skip:
        If True and email is disabled, raise ``EmailNotConfiguredError``.
        Default False → soft skip for local/dev.

    Returns
    -------
    EmailSendResult
        ``sent=True`` on success; ``skipped=True`` when email is disabled.
    """
    if not settings.email_enabled:
        detail = "EMAIL_ENABLED is false; email not sent."
        logger.info(
            "email_skipped reason=disabled to=%s subject=%r",
            [a.email for a in payload.to],
            payload.subject,
        )
        if raise_on_skip:
            raise EmailNotConfiguredError(detail)
        return EmailSendResult(sent=False, skipped=True, detail=detail)

    if not settings.smtp_host or not settings.email_from_address:
        detail = "Email enabled but SMTP_HOST / EMAIL_FROM_ADDRESS missing."
        logger.error("email_misconfigured: %s", detail)
        raise EmailNotConfiguredError(detail)

    if not settings.smtp_password:
        detail = "Email enabled but SMTP_PASSWORD is not set (use Gmail App Password on Railway)."
        logger.error("email_misconfigured: %s", detail)
        raise EmailNotConfiguredError(detail)

    mime = _build_mime_message(payload)
    recipients = _all_envelope_recipients(payload)
    message_id: Optional[str] = mime["Message-ID"]

    last_exc: BaseException | None = None
    for idx, (port, start_tls, use_ssl) in enumerate(_smtp_attempts()):
        try:
            await _smtp_send_once(
                mime,
                recipients=recipients,
                port=port,
                start_tls=start_tls,
                use_ssl=use_ssl,
            )
            if idx > 0:
                logger.warning(
                    "email_sent_via_fallback host=%s port=%s start_tls=%s ssl=%s",
                    settings.smtp_host,
                    port,
                    start_tls,
                    use_ssl,
                )
            logger.info(
                "email_sent to=%s subject=%r message_id=%s port=%s",
                recipients,
                payload.subject,
                message_id,
                port,
            )
            return EmailSendResult(
                sent=True,
                skipped=False,
                detail="Email sent.",
                message_id=str(message_id) if message_id else None,
            )
        except EmailError:
            raise
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "email_smtp_attempt_failed host=%s port=%s start_tls=%s ssl=%s err=%s",
                settings.smtp_host,
                port,
                start_tls,
                use_ssl,
                exc,
            )
            # Only fall through to next attempt on connect/timeout style failures
            if not _is_connect_timeout(exc) and idx == 0:
                # Auth / recipient errors — don't retry other ports
                if "authentication" in str(exc).lower() or "535" in str(exc):
                    break
            continue

    logger.exception(
        "email_delivery_failed to=%s subject=%r",
        recipients,
        payload.subject,
    )
    raise EmailDeliveryError(f"Failed to send email: {last_exc}") from last_exc


async def send_simple_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    to_name: Optional[str] = None,
    html_body: Optional[str] = None,
    raise_on_skip: bool = False,
) -> EmailSendResult:
    """Convenience wrapper when you only need one recipient + subject + body."""
    return await send_email(
        OutgoingEmail(
            to=[EmailAddress(email=to_email, name=to_name)],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        ),
        raise_on_skip=raise_on_skip,
    )
