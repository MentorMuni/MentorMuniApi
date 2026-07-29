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


def build_activation_url(raw_token: str) -> str:
    """
    Build the FE activation URL.

    Default base: https://www.mentormuni.com
    Final link: {base}/activate-tpo?token=...
    """
    base = (settings.org_portal_base_url or "https://www.mentormuni.com").rstrip("/")
    query = urlencode({"token": raw_token})
    path = (settings.tpo_activation_path or "/activate-tpo").strip()
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}?{query}"


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
    display_name = f"{first_name} {last_name}".strip() or "there"
    activate_url = build_activation_url(raw_token)
    expires_label = expires_at.strftime("%d %b %Y %H:%M UTC")
    action = "re-activate" if is_reinvite else "activate"
    brand = brand_from_name()

    subject = (
        f"Re-activate your MentorMuni TPO account — {organization_name}"
        if is_reinvite
        else f"Activate your MentorMuni TPO account — {organization_name}"
    )

    text_body = f"""Hi {display_name},

You have been invited as the TPO (Organization Admin) for {organization_name} on MentorMuni.

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
  <p>You have been invited as the <strong>TPO (Organization Admin)</strong> for
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
