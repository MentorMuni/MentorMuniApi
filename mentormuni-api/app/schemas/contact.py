import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ContactSubmitRequest(BaseModel):
    """Contact/enroll form submission."""
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., max_length=255)
    phone: str = Field(..., min_length=8, max_length=20)
    year: Optional[str] = Field(None, max_length=50, description="Academic year e.g. 3rd year, Final year")
    message: Optional[str] = Field(None, max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v
