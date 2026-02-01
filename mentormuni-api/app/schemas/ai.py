from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal

USER_TYPES = Literal["student", "working professional"]
VALID_ANSWERS = {"Yes", "No"}


class AIRequest(BaseModel):
    prompt: str
    use_case: str


class AIResponse(BaseModel):
    output: str


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
    user_type: str = Field(..., description="student or working professional")
    experience_years: int = Field(..., ge=0, le=50)
    primary_skill: str = Field(..., min_length=1, max_length=100)
    target_role: str = Field(..., min_length=1, max_length=100)

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower not in ("student", "working professional"):
            raise ValueError("user_type must be 'student' or 'working professional'")
        return v_lower


class PlanResponse(BaseModel):
    evaluation_plan: List[str]


class EvaluateRequest(BaseModel):
    questions: List[str] = Field(..., min_length=1)
    answers: List[str] = Field(..., min_length=1)

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

    @field_validator("questions")
    @classmethod
    def validate_questions_no_empty(cls, v: List[str]) -> List[str]:
        for i, q in enumerate(v):
            if not (q and str(q).strip()):
                raise ValueError(f"question at index {i} cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_matching_length(self):
        if len(self.questions) != len(self.answers):
            raise ValueError("questions and answers must have the same length (no partial submissions)")
        return self