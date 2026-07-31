"""Reusable email content builders (subject + bodies). Customize per flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from app.core.config import settings


@dataclass(frozen=True)
class RenderedEmailContent:
    subject: str
    text_body: str
    html_body: str


def brand_from_name() -> str:
    return (settings.email_from_name or "MentorMuni Team").strip() or "MentorMuni Team"


def email_signature_text() -> str:
    """Shared text signature for all product emails."""
    name = brand_from_name()
    support = (settings.email_reply_to or settings.email_from_address or "").strip()
    lines = [
        "Warm regards,",
        f"The {name}",
        "",
        "MentorMuni — AI mentorship for campus placements & career readiness",
    ]
    if support:
        lines.append(f"Email: {support}")
    return "\n".join(lines)


def email_signature_html() -> str:
    """Shared HTML signature for all product emails."""
    name = brand_from_name()
    support = (settings.email_reply_to or settings.email_from_address or "").strip()
    support_line = (
        f'<br/><a href="mailto:{support}" style="color:#555;">{support}</a>'
        if support
        else ""
    )
    return f"""
  <div style="margin-top:28px;padding-top:16px;border-top:1px solid #e5e5e5;font-size:13px;color:#444;line-height:1.5;">
    <p style="margin:0 0 4px 0;">Warm regards,</p>
    <p style="margin:0 0 12px 0;"><strong>The {name}</strong></p>
    <p style="margin:0;color:#666;">
      MentorMuni — AI mentorship for campus placements &amp; career readiness
      {support_line}
    </p>
  </div>
"""


def build_activation_url(raw_token: str, *, path: str | None = None) -> str:
    """
    Build the FE activation URL.

    path overrides: TPO → /activate-tpo, HOD → /activate-hod
    """
    base = (settings.org_portal_base_url or "https://www.mentormuni.com").rstrip("/")
    query = urlencode({"token": raw_token})
    resolved = (
        path
        or settings.staff_activation_path
        or settings.hod_activation_path
        or settings.tpo_activation_path
        or "/activate-hod"
    ).strip()
    if not resolved.startswith("/"):
        resolved = "/" + resolved
    return f"{base}{resolved}?{query}"


def build_tpo_activation_url(raw_token: str) -> str:
    return build_activation_url(raw_token, path=settings.tpo_activation_path or "/activate-tpo")


def build_hod_activation_url(raw_token: str) -> str:
    return build_activation_url(
        raw_token,
        path=settings.hod_activation_path or settings.staff_activation_path or "/activate-hod",
    )


def build_student_activation_url(raw_token: str) -> str:
    return build_activation_url(
        raw_token,
        path=settings.student_activation_path or "/studentportal/set-password",
    )


def render_tpo_activation_email(
    *,
    first_name: str,
    last_name: str,
    username: str,
    organization_name: str,
    raw_token: str,
    expires_at: datetime,
    is_reinvite: bool = False,
) -> RenderedEmailContent:
    """TPO invite / reinvite — set your own password via activation link."""
    return render_staff_activation_email(
        first_name=first_name,
        last_name=last_name,
        username=username,
        organization_name=organization_name,
        role_label="TPO (Organization Admin)",
        raw_token=raw_token,
        expires_at=expires_at,
        is_reinvite=is_reinvite,
        activation_path=settings.tpo_activation_path or "/activate-tpo",
    )


def render_staff_activation_email(
    *,
    first_name: str,
    last_name: str,
    username: str,
    organization_name: str,
    role_label: str,
    raw_token: str,
    expires_at: datetime,
    is_reinvite: bool = False,
    activation_path: str | None = None,
) -> RenderedEmailContent:
    display_name = f"{first_name} {last_name}".strip() or "there"
    activate_url = build_activation_url(
        raw_token,
        path=activation_path
        or settings.hod_activation_path
        or settings.staff_activation_path
        or "/activate-hod",
    )
    expires_label = expires_at.strftime("%d %b %Y %H:%M UTC")
    action = "re-activate" if is_reinvite else "activate"

    subject = (
        f"Re-activate your MentorMuni {role_label} account — {organization_name}"
        if is_reinvite
        else f"Activate your MentorMuni {role_label} account — {organization_name}"
    )

    text_body = f"""Hi {display_name},

You have been invited as {role_label} for {organization_name} on MentorMuni.

Username: {username}

Please {action} your account and set your password using this link:
{activate_url}

This link expires on {expires_label}.

If you did not expect this email, you can ignore it or reply to this message.

{email_signature_text()}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; color: #111;">
  <p>Hi {display_name},</p>
  <p>You have been invited as <strong>{role_label}</strong> for
     <strong>{organization_name}</strong> on MentorMuni.</p>
  <p><strong>Username:</strong> {username}</p>
  <p>Please {action} your account and set your password:</p>
  <p><a href="{activate_url}" style="display:inline-block;padding:10px 16px;background:#111;color:#fff;text-decoration:none;border-radius:6px;">
    Set password &amp; activate
  </a></p>
  <p style="font-size:13px;color:#555;">Or open this link:<br/>
    <a href="{activate_url}">{activate_url}</a>
  </p>
  <p style="font-size:13px;color:#555;">This link expires on <strong>{expires_label}</strong>.</p>
  <p style="font-size:13px;color:#777;">If you did not expect this email, you can ignore it or reply to this message.</p>
  {email_signature_html()}
</body>
</html>
"""
    return RenderedEmailContent(subject=subject, text_body=text_body, html_body=html_body)


def render_student_activation_email(
    *,
    first_name: str,
    last_name: str,
    username: str,
    organization_name: str,
    department_name: str | None,
    raw_token: str,
    expires_at: datetime,
) -> RenderedEmailContent:
    display_name = f"{first_name} {last_name}".strip() or "there"
    activate_url = build_student_activation_url(raw_token)
    expires_label = expires_at.strftime("%d %b %Y %H:%M UTC")
    dept_line = f" ({department_name})" if department_name else ""

    subject = f"Set your MentorMuni student password — {organization_name}"
    text_body = f"""Hi {display_name},

Your student account for {organization_name}{dept_line} on MentorMuni is ready.

Username: {username}

Set your password using this link:
{activate_url}

This link expires on {expires_label}.

Then log in at the Student Portal with your college and credentials.

{email_signature_text()}
"""
    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; color: #111;">
  <p>Hi {display_name},</p>
  <p>Your student account for <strong>{organization_name}</strong>{f' — <strong>{department_name}</strong>' if department_name else ''}
     on MentorMuni is ready.</p>
  <p><strong>Username:</strong> {username}</p>
  <p>Set your password:</p>
  <p><a href="{activate_url}" style="display:inline-block;padding:10px 16px;background:#111;color:#fff;text-decoration:none;border-radius:6px;">
    Set password
  </a></p>
  <p style="font-size:13px;color:#555;">Or open this link:<br/>
    <a href="{activate_url}">{activate_url}</a>
  </p>
  <p style="font-size:13px;color:#555;">This link expires on <strong>{expires_label}</strong>.</p>
  {email_signature_html()}
</body>
</html>
"""
    return RenderedEmailContent(subject=subject, text_body=text_body, html_body=html_body)


def build_password_reset_url(raw_token: str) -> str:
    base = (settings.org_portal_base_url or "https://www.mentormuni.com").rstrip("/")
    query = urlencode({"token": raw_token})
    path = (settings.password_reset_path or "/reset-password").strip()
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}?{query}"


def render_password_reset_email(
    *,
    first_name: str,
    last_name: str,
    organization_name: str,
    raw_token: str,
    expires_at: datetime,
) -> RenderedEmailContent:
    display_name = f"{first_name} {last_name}".strip() or "there"
    reset_url = build_password_reset_url(raw_token)
    expires_label = expires_at.strftime("%d %b %Y %H:%M UTC")

    subject = f"Reset your MentorMuni password — {organization_name}"
    text_body = f"""Hi {display_name},

We received a request to reset your MentorMuni password for {organization_name}.

Reset your password using this link:
{reset_url}

This link expires on {expires_label}.

If you did not request this, you can ignore this email.

{email_signature_text()}
"""
    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; color: #111;">
  <p>Hi {display_name},</p>
  <p>We received a request to reset your MentorMuni password for
     <strong>{organization_name}</strong>.</p>
  <p><a href="{reset_url}" style="display:inline-block;padding:10px 16px;background:#111;color:#fff;text-decoration:none;border-radius:6px;">
    Reset password
  </a></p>
  <p style="font-size:13px;color:#555;">Or open this link:<br/>
    <a href="{reset_url}">{reset_url}</a>
  </p>
  <p style="font-size:13px;color:#555;">This link expires on <strong>{expires_label}</strong>.</p>
  <p style="font-size:13px;color:#777;">If you did not request this, you can ignore this email.</p>
  {email_signature_html()}
</body>
</html>
"""
    return RenderedEmailContent(subject=subject, text_body=text_body, html_body=html_body)
