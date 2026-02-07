from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal, Optional

USER_TYPES = Literal["student", "working professional"]
VALID_ANSWERS = {"Yes", "No"}


class LearningRecommendation(BaseModel):
    priority: str
    topic: str
    why: str


class EvaluateResponse(BaseModel):
    readiness_percentage: int
    readiness_label: str
    strengths: List[str]
    gaps: List[str]
    learning_recommendations: List[LearningRecommendation]


class PlanRequest(BaseModel):
    user_type: str = Field(
        ...,
        description="e.g. 'student', 'working professional', '3rd Year Student', '4th Year Student'",
    )
    experience_years: Optional[int] = Field(
        default=0,
        ge=0,
        le=50,
        description="Optional. Default 0 for students, 1 for working professionals if omitted.",
    )
    primary_skill: str = Field(..., min_length=1, max_length=100)
    target_role: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional. Defaults to '{primary_skill} Developer' if omitted or empty.",
    )

    @field_validator("target_role")
    @classmethod
    def target_role_empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip()
    email: Optional[str] = Field(default=None, max_length=255, description="Optional. Omit or send null/empty if not collected.")
    phone: Optional[str] = Field(default=None, max_length=20, description="Optional. Omit or send null/empty if not collected.")

    @field_validator("email", "phone")
    @classmethod
    def empty_to_none(cls, v):
        """Treat empty string, blank, or null as None."""
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower in ("working professional", "workingprofessional"):
            return "working professional"
        if v_lower in ("3rd year student", "4th year student", "final year student", "student"):
            return "student"
        raise ValueError(
            "user_type must be one of: student, working professional, 3rd Year Student, 4th Year Student"
        )

    @model_validator(mode="after")
    def set_target_role_default(self):
        """Default target_role to '{primary_skill} Developer' when omitted."""
        if not self.target_role or not str(self.target_role).strip():
            object.__setattr__(self, "target_role", f"{self.primary_skill} Developer")
        return self


class QuestionItem(BaseModel):
    """Single question with its correct factual answer and study topic."""
    question: str = Field(..., min_length=1)
    correct_answer: Literal["Yes", "No"]
    study_topic: str = Field(..., min_length=1, description="Short topic name for study/recommendations (e.g. 'Dependency Injection', 'Scoped Services')")


class PlanResponse(BaseModel):
    evaluation_plan: List[QuestionItem]


class EvaluateRequest(BaseModel):
    questions: List[str] = Field(..., min_length=1)
    answers: List[str] = Field(..., min_length=1)
    correct_answers: List[str] = Field(..., min_length=1, description="Expected answer per question from Plan")
    study_topics: List[str] = Field(..., min_length=1, description="Study topic per question from Plan (for strengths/gaps/recommendations)")

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v: List[str]) -> List[str]:
        normalized = []
        for i, ans in enumerate(v):
            ans_stripped = str(ans).strip() if ans is not None else ""
            if not ans_stripped:
                raise ValueError(f"answer at index {i} cannot be empty")
            if ans_stripped not in VALID_ANSWERS:
                raise ValueError(f"answer at index {i} must be 'Yes' or 'No', got: {ans_stripped!r}")
            normalized.append(ans_stripped)
        return normalized

    @field_validator("study_topics")
    @classmethod
    def validate_study_topics_no_empty(cls, v: List[str]) -> List[str]:
        for i, t in enumerate(v):
            if not (t and str(t).strip()):
                raise ValueError(f"study_topics[{i}] cannot be empty")
        return v

    @field_validator("correct_answers")
    @classmethod
    def validate_correct_answers(cls, v: List[str]) -> List[str]:
        for i, ans in enumerate(v):
            a = str(ans).strip() if ans is not None else ""
            if a not in VALID_ANSWERS:
                raise ValueError(f"correct_answers[{i}] must be 'Yes' or 'No', got: {ans!r}")
        return v

    @field_validator("questions")
    @classmethod
    def validate_questions_no_empty(cls, v: List[str]) -> List[str]:
        for i, q in enumerate(v):
            if not (q and str(q).strip()):
                raise ValueError(f"question at index {i} cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_matching_length(self):
        n = len(self.questions)
        if len(self.answers) != n:
            raise ValueError("questions and answers must have the same length")
        if len(self.correct_answers) != n:
            raise ValueError("correct_answers must have the same length as questions")
        if len(self.study_topics) != n:
            raise ValueError("study_topics must have the same length as questions")
        return self