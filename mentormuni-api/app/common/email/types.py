"""
Common outbound email primitives.

Callers customize ``to``, ``subject``, and body (text and/or HTML).
Transport is configured once via Settings (SMTP).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class EmailAddress:
    """Single mailbox: ``Name <addr@host>`` or bare address."""

    email: str
    name: Optional[str] = None

    def formatted(self) -> str:
        address = self.email.strip()
        if self.name and self.name.strip():
            return f"{self.name.strip()} <{address}>"
        return address


@dataclass
class OutgoingEmail:
    """
    Fully customizable outbound message.

    Provide at least one of ``text_body`` / ``html_body``.
    """

    to: Sequence[EmailAddress]
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    cc: Sequence[EmailAddress] = field(default_factory=tuple)
    bcc: Sequence[EmailAddress] = field(default_factory=tuple)
    reply_to: Optional[EmailAddress] = None
    # Optional override; defaults to Settings.email_from_*
    from_address: Optional[EmailAddress] = None

    def __post_init__(self) -> None:
        if not self.to:
            raise ValueError("OutgoingEmail.to must contain at least one recipient.")
        if not (self.text_body or self.html_body):
            raise ValueError("OutgoingEmail requires text_body and/or html_body.")
        if not (self.subject and self.subject.strip()):
            raise ValueError("OutgoingEmail.subject is required.")


@dataclass(frozen=True)
class EmailSendResult:
    """Outcome of an attempted send (including intentional skip)."""

    sent: bool
    skipped: bool = False
    detail: str = ""
    message_id: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.sent or self.skipped
