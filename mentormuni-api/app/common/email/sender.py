"""
Async email sender — shared by all product flows.

Transports (auto-selected):
  1. Resend HTTP API when ``RESEND_API_KEY`` is set (preferred on Railway).
  2. SMTP (Gmail etc.) when only ``SMTP_PASSWORD`` is set — often blocked on Railway.

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

When ``EMAIL_ENABLED=false``, ``send_email`` returns ``skipped=True`` and does not raise.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Optional

import aiosmtplib
import httpx

from app.common.email.exceptions import (
    EmailDeliveryError,
    EmailError,
    EmailNotConfiguredError,
)
from app.common.email.types import EmailAddress, EmailSendResult, OutgoingEmail
from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def is_email_enabled() -> bool:
    return bool(settings.email_enabled)


def _has_resend() -> bool:
    return bool((settings.resend_api_key or "").strip())


def _has_smtp() -> bool:
    return bool(
        settings.smtp_host
        and settings.email_from_address
        and (settings.smtp_password or "").strip()
    )


def is_email_configured() -> bool:
    """True when we can attempt a send (enabled + Resend or SMTP)."""
    return bool(settings.email_enabled and settings.email_from_address and (_has_resend() or _has_smtp()))


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
    name = type(exc).__name__.lower()
    return "timeout" in name


def _smtp_attempts() -> list[tuple[int, bool, bool]]:
    """Ordered (port, start_tls, use_ssl) attempts — configured port only."""
    primary_start_tls = settings.smtp_use_tls and not settings.smtp_use_ssl
    primary = (int(settings.smtp_port), primary_start_tls, bool(settings.smtp_use_ssl))

    host = (settings.smtp_host or "").lower()
    is_gmail = "gmail.com" in host or "google.com" in host
    if is_gmail and primary[0] == 587:
        return [(465, False, True), primary]
    return [primary]


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


async def _send_via_resend(payload: OutgoingEmail) -> EmailSendResult:
    """Send via Resend HTTPS API — works from Railway where Gmail SMTP does not."""
    api_key = (settings.resend_api_key or "").strip()
    if not api_key:
        raise EmailNotConfiguredError("RESEND_API_KEY is not set.")

    sender = payload.from_address or _default_from_address()
    if not sender.email:
        raise EmailNotConfiguredError("EMAIL_FROM_ADDRESS is not set.")

    body: dict = {
        "from": _format_address(sender),
        "to": [_format_address(a) for a in payload.to],
        "subject": payload.subject.strip(),
    }
    if payload.html_body:
        body["html"] = payload.html_body
    if payload.text_body:
        body["text"] = payload.text_body
    if payload.cc:
        body["cc"] = [_format_address(a) for a in payload.cc]
    if payload.bcc:
        body["bcc"] = [_format_address(a) for a in payload.bcc]

    reply = payload.reply_to
    if reply is None and settings.email_reply_to:
        reply = EmailAddress(email=settings.email_reply_to)
    if reply is not None:
        body["reply_to"] = _format_address(reply)

    timeout = float(min(max(settings.smtp_timeout_seconds, 8), 30))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
    except httpx.TimeoutException as exc:
        raise EmailDeliveryError(
            f"Resend API timed out after {timeout}s: {exc}"
        ) from exc
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(f"Resend API request failed: {exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text
        try:
            data = resp.json()
            detail = data.get("message") or data.get("error") or detail
        except Exception:
            pass
        logger.error(
            "email_resend_failed status=%s to=%s detail=%s",
            resp.status_code,
            [a.email for a in payload.to],
            detail,
        )
        raise EmailDeliveryError(f"Resend failed ({resp.status_code}): {detail}")

    message_id = None
    try:
        message_id = str((resp.json() or {}).get("id") or "") or None
    except Exception:
        pass

    logger.info(
        "email_sent via=resend to=%s subject=%r message_id=%s",
        [a.email for a in payload.to],
        payload.subject,
        message_id,
    )
    return EmailSendResult(
        sent=True,
        skipped=False,
        detail="Email sent via Resend.",
        message_id=message_id,
    )


async def _send_via_smtp(payload: OutgoingEmail) -> EmailSendResult:
    if not settings.smtp_host or not settings.email_from_address:
        raise EmailNotConfiguredError("Email enabled but SMTP_HOST / EMAIL_FROM_ADDRESS missing.")
    if not settings.smtp_password:
        raise EmailNotConfiguredError(
            "Email enabled but neither RESEND_API_KEY nor SMTP_PASSWORD is set."
        )

    mime = _build_mime_message(payload)
    recipients = _all_envelope_recipients(payload)
    message_id: Optional[str] = mime["Message-ID"]

    last_exc: BaseException | None = None
    attempted_ports: list[int] = []
    for idx, (port, start_tls, use_ssl) in enumerate(_smtp_attempts()):
        attempted_ports.append(port)
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
                "email_sent via=smtp to=%s subject=%r message_id=%s port=%s",
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
            if not _is_connect_timeout(exc) and idx == 0:
                if "authentication" in str(exc).lower() or "535" in str(exc):
                    break
            continue

    logger.exception(
        "email_delivery_failed to=%s subject=%r ports=%s",
        recipients,
        payload.subject,
        attempted_ports,
    )
    ports_txt = ",".join(str(p) for p in attempted_ports) or str(settings.smtp_port)
    hint = ""
    if last_exc is not None and _is_connect_timeout(last_exc):
        hint = (
            " Railway often blocks Gmail SMTP — set RESEND_API_KEY and use Resend, "
            "or share the activation link manually."
        )
    raise EmailDeliveryError(
        f"Failed to send email via {settings.smtp_host}:{ports_txt}: {last_exc}.{hint}"
    ) from last_exc


async def send_email(
    payload: OutgoingEmail,
    *,
    raise_on_skip: bool = False,
) -> EmailSendResult:
    """
    Send a customized email via Resend (preferred) or SMTP.

    Parameters
    ----------
    payload:
        Recipients + subject + body (caller-owned content).
    raise_on_skip:
        If True and email is disabled, raise ``EmailNotConfiguredError``.
        Default False → soft skip for local/dev.
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

    if not settings.email_from_address:
        detail = "Email enabled but EMAIL_FROM_ADDRESS is missing."
        logger.error("email_misconfigured: %s", detail)
        raise EmailNotConfiguredError(detail)

    if _has_resend():
        return await _send_via_resend(payload)

    if _has_smtp():
        return await _send_via_smtp(payload)

    detail = (
        "Email enabled but no transport configured. "
        "Set RESEND_API_KEY (recommended on Railway) or SMTP_PASSWORD."
    )
    logger.error("email_misconfigured: %s", detail)
    raise EmailNotConfiguredError(detail)


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
