"""POST /api/inquiries — waitlist + contact (intent-branched)."""

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class InquiryCreate(BaseModel):
    intent: Literal["waitlist", "contact"]
    source: str = Field(..., min_length=1, max_length=200)
    submitted_at: str = Field(..., min_length=1, max_length=64)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    college: Optional[str] = None
    year: Optional[str] = None
    target_role: Optional[str] = None
    whatsapp_opt_in: Optional[bool] = None
    message: Optional[str] = None
    topic: Optional[Literal["colleges"]] = None
    audience: Optional[Literal["students", "colleges"]] = None
    score: Optional[Any] = None

    @field_validator(
        "name",
        "email",
        "phone",
        "college",
        "year",
        "target_role",
        "message",
        "source",
        "submitted_at",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return None if s == "" else s
        return v

    @field_validator("topic", "audience", mode="before")
    @classmethod
    def strip_optional_literals(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            s = v.strip()
            return None if s == "" else s
        return v

    @staticmethod
    def _present(v) -> bool:
        return v is not None and (not isinstance(v, str) or bool(str(v).strip()))

    @model_validator(mode="after")
    def validate_by_intent(self):
        if self.intent == "contact":
            missing = []
            for key in ("name", "email", "phone", "message"):
                if not self._present(getattr(self, key)):
                    missing.append(key)
            if missing:
                raise ValueError(
                    f"For intent=contact, required fields missing or empty: {', '.join(missing)}"
                )
            em = self.email
            if em is not None and not re.match(r"^[^@]+@[^@]+\.[^@]+$", em):
                raise ValueError("Invalid email format")
        else:
            missing = []
            for key in ("name", "phone", "college", "year", "target_role"):
                if not self._present(getattr(self, key)):
                    missing.append(key)
            if missing:
                raise ValueError(
                    f"For intent=waitlist, required fields missing or empty: {', '.join(missing)}"
                )
        return self
