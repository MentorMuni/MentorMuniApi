"""Email send errors."""

from __future__ import annotations


class EmailError(Exception):
    """Base error for the common email layer."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmailNotConfiguredError(EmailError):
    """SMTP / from-address not configured while email is enabled."""


class EmailDeliveryError(EmailError):
    """SMTP accepted the connection but delivery failed."""
