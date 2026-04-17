from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Annotated, List, Literal, Optional, Union

USER_TYPES = Literal[
    "college_student_year_1",
    "college_student_year_2",
    "college_student_year_3",
    "college_student_year_4",
    "recent_graduate",
    "it_professional",
]

VALID_EVAL_ANSWERS = {"Yes", "No", "A", "B", "C", "D"}


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
        description=(
            "college_student_year_1 … college_student_year_4, or it_professional "
            "(legacy: student, 3rd/4th year student, working professional — normalized to canonical values)"
        ),
    )
    experience_years: Optional[int] = Field(
        default=0,
        ge=0,
        le=50,
        description="Optional. Default 0 for students, 1 for working professionals if omitted.",
    )
    primary_skill: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Technical skill e.g. React, .NET, Python (any tech stack allowed)",
    )

    @field_validator("primary_skill")
    @classmethod
    def validate_primary_skill_is_safe(cls, v: str) -> str:
        from app.validators.primary_skill import validate_primary_skill as _validate
        return _validate(v)
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
        from app.validators.user_type import normalize_user_type

        return normalize_user_type(v)

    @model_validator(mode="after")
    def set_target_role_default(self):
        """Default target_role to '{primary_skill} Developer' when omitted."""
        if not self.target_role or not str(self.target_role).strip():
            object.__setattr__(self, "target_role", f"{self.primary_skill} Developer")
        return self


class InterviewReadinessPlanRequest(BaseModel):
    """
    POST /interview-ready/interview-readiness/plan — placement-aware holistic readiness.
    Optional step-13 fields: only sent for 4th year / recent graduate (placement) or professionals (pro).
    """

    user_type: str = Field(
        ...,
        description="Canonical or legacy label (e.g. 3rd Year Student, Recent Graduate, working professional).",
    )
    experience_years: Optional[int] = Field(default=0, ge=0, le=50)
    primary_skill: str = Field(
        ...,
        min_length=2,
        max_length=400,
        description="Focus areas / stack (comma-separated OK, e.g. DSA, OOP, DBMS).",
    )
    target_role: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    college_name: Optional[str] = Field(default=None, max_length=200)
    assessment_focus: Optional[str] = Field(default=None, max_length=100)
    current_organization: Optional[str] = Field(default=None, max_length=200)
    user_category: Optional[str] = Field(
        default=None,
        description="3rd_year | 4th_year | recent_graduate | working_professional — inferred if omitted",
    )
    campus_or_off_campus: Optional[Literal["campus", "off_campus"]] = Field(
        default=None,
        description="Placement context: 4th year / recent graduate",
    )
    targets_service_mnc: Optional[bool] = Field(default=None)
    targets_product_company: Optional[bool] = Field(default=None)
    target_companies_notes: Optional[str] = Field(default=None, max_length=2000)
    specific_role_requested: Optional[bool] = Field(default=None)
    specific_role: Optional[str] = Field(default=None, max_length=200)
    core_skill: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Professional: main stack focus (optional)",
    )
    jd_provided: Optional[bool] = Field(default=None)
    job_description: Optional[str] = Field(default=None, max_length=12000)
    target_company_name: Optional[str] = Field(default=None, max_length=200)

    @field_validator("primary_skill")
    @classmethod
    def validate_primary_skill_is_safe(cls, v: str) -> str:
        from app.validators.primary_skill import validate_primary_skill as _validate

        return _validate(v)

    @field_validator(
        "target_role",
        "college_name",
        "assessment_focus",
        "current_organization",
        "target_companies_notes",
        "specific_role",
        "core_skill",
        "job_description",
        "target_company_name",
    )
    @classmethod
    def strip_optional_strings(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("email", "phone")
    @classmethod
    def empty_to_none_contact(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: str) -> str:
        from app.validators.user_type import normalize_user_type

        return normalize_user_type(v)

    @field_validator("user_category", mode="before")
    @classmethod
    def normalize_user_category(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not str(v).strip():
            return None
        key = str(v).lower().strip().replace(" ", "_").replace("-", "_")
        aliases = {
            "1st_to_3rd_year": "3rd_year",
            "first_to_third_year": "3rd_year",
            "fourth_year": "4th_year",
            "year_4": "4th_year",
        }
        if key in aliases:
            key = aliases[key]
        allowed = {"3rd_year", "4th_year", "recent_graduate", "working_professional"}
        if key not in allowed:
            raise ValueError(
                "user_category must be one of: 3rd_year, 4th_year, recent_graduate, working_professional"
            )
        return key

    @field_validator("campus_or_off_campus", mode="before")
    @classmethod
    def normalize_campus(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not str(v).strip():
            return None
        if v in ("campus", "off_campus"):
            return v
        s = str(v).lower().strip().replace(" ", "_").replace("-", "_")
        if s in ("off_campus", "offcampus"):
            return "off_campus"
        if s == "campus":
            return "campus"
        raise ValueError('campus_or_off_campus must be "campus" or "off_campus"')

    @model_validator(mode="after")
    def infer_category_and_target_role(self):
        from app.validators.user_type import infer_interview_user_category

        if self.user_category is None:
            object.__setattr__(
                self,
                "user_category",
                infer_interview_user_category(self.user_type),
            )
        if not self.target_role or not str(self.target_role).strip():
            object.__setattr__(self, "target_role", f"{self.primary_skill} Developer")
        return self


class LegacyPlanQuestionItem(BaseModel):
    """Original /interview-ready/plan item: only Yes/No questions (no question_type)."""

    question: str = Field(..., min_length=1)
    correct_answer: Literal["Yes", "No"]
    study_topic: str = Field(
        ...,
        min_length=1,
        description="Short topic name for study/recommendations",
    )


class YesNoQuestionItem(BaseModel):
    """Yes/No screening question."""

    question_type: Literal["yes_no"] = "yes_no"
    question: str = Field(..., min_length=1)
    correct_answer: Literal["Yes", "No"]
    study_topic: str = Field(
        ...,
        min_length=1,
        description="Short topic name for study/recommendations",
    )


class MultipleChoiceQuestionItem(BaseModel):
    """Single-select multiple choice (exactly four options, labeled A–D in order)."""

    question_type: Literal["multiple_choice"] = "multiple_choice"
    question: str = Field(..., min_length=1)
    options: List[str] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Four choices in order A, B, C, D",
    )
    correct_answer: Literal["A", "B", "C", "D"]
    study_topic: str = Field(..., min_length=1)

    @field_validator("options")
    @classmethod
    def each_option_non_empty(cls, v: List[str]) -> List[str]:
        out = []
        for i, o in enumerate(v):
            t = str(o).strip() if o is not None else ""
            if not t:
                raise ValueError(f"options[{i}] cannot be empty")
            if len(t) > 400:
                raise ValueError(f"options[{i}] is too long (max 400 characters)")
            out.append(t)
        return out


QuestionItem = Annotated[
    Union[YesNoQuestionItem, MultipleChoiceQuestionItem],
    Field(discriminator="question_type"),
]


class SkillReadinessPlanRequest(BaseModel):
    """Request body for POST /interview-ready/skill-readiness/plan (rigorous skill-depth quiz)."""

    user_type: str = Field(
        ...,
        description=(
            'One of: college_student_year_1, college_student_year_2, college_student_year_3, '
            "college_student_year_4, it_professional"
        ),
    )
    experience_years: Optional[int] = Field(
        default=0,
        ge=0,
        le=50,
        description="Years of experience (0 for early college; use actual YOE for professionals).",
    )
    primary_skill: str = Field(..., min_length=1, max_length=100)
    target_role: Optional[str] = Field(default=None, max_length=100)
    target_company_type: str = Field(
        default="both",
        description='One of: "service_mnc", "product_company", "both". Defaults to "both".',
    )
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("primary_skill")
    @classmethod
    def validate_primary_skill_is_safe(cls, v: str) -> str:
        from app.validators.primary_skill import validate_primary_skill as _validate
        return _validate(v)

    @field_validator("target_role")
    @classmethod
    def target_role_empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip()

    @field_validator("email", "phone")
    @classmethod
    def empty_to_none(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("user_type")
    @classmethod
    def validate_skill_user_type(cls, v: str) -> str:
        from app.validators.user_type import normalize_user_type

        return normalize_user_type(v)

    @field_validator("target_company_type", mode="before")
    @classmethod
    def validate_target_company_type(cls, v) -> str:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return "both"
        key = str(v).lower().strip().replace(" ", "_").replace("-", "_")
        allowed = {"service_mnc", "product_company", "both"}
        if key not in allowed:
            raise ValueError('target_company_type must be one of: service_mnc, product_company, both')
        return key

    @model_validator(mode="after")
    def set_target_role_default(self):
        if not self.target_role or not str(self.target_role).strip():
            object.__setattr__(self, "target_role", f"{self.primary_skill} Developer")
        return self


class AptitudeReadinessPlanRequest(BaseModel):
    """Request body for POST /interview-ready/aptitude-readiness/plan."""

    user_type: str = Field(
        ...,
        description=(
            'One of: college_student_year_1, college_student_year_2, college_student_year_3, '
            "college_student_year_4, it_professional"
        ),
    )
    experience_years: Optional[int] = Field(default=0, ge=0, le=50)
    primary_skill: str = Field(
        default="Quantitative, Logical and Verbal Reasoning",
        min_length=1,
        max_length=200,
        description="Defaults to aptitude tracks: Quantitative, Logical and Verbal Reasoning.",
    )
    target_role: Optional[str] = Field(default="Software Engineer", max_length=100)
    target_company_type: str = Field(
        default="both",
        description='One of: "service_mnc", "product_company", "both". Defaults to "both".',
    )
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("target_role")
    @classmethod
    def target_role_empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip()

    @field_validator("email", "phone")
    @classmethod
    def empty_to_none(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("user_type")
    @classmethod
    def validate_skill_user_type(cls, v: str) -> str:
        from app.validators.user_type import normalize_user_type

        return normalize_user_type(v)

    @field_validator("target_company_type", mode="before")
    @classmethod
    def validate_target_company_type(cls, v) -> str:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return "both"
        key = str(v).lower().strip().replace(" ", "_").replace("-", "_")
        allowed = {"service_mnc", "product_company", "both"}
        if key not in allowed:
            raise ValueError('target_company_type must be one of: service_mnc, product_company, both')
        return key

    @model_validator(mode="after")
    def set_target_role_default(self):
        if not self.target_role or not str(self.target_role).strip():
            object.__setattr__(self, "target_role", "Software Engineer")
        if not self.primary_skill or not str(self.primary_skill).strip():
            object.__setattr__(self, "primary_skill", "Quantitative, Logical and Verbal Reasoning")
        return self


class SkillReadinessYesNoItem(BaseModel):
    question_type: Literal["yes_no"] = "yes_no"
    question: str = Field(..., min_length=1)
    correct_answer: Literal["Yes", "No"]
    study_topic: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)


class SkillReadinessMcBase(BaseModel):
    """Shared shape for multiple_choice, scenario, and code_mcq."""

    question: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_answer: Literal["A", "B", "C", "D"]
    study_topic: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)

    @field_validator("options")
    @classmethod
    def each_option_non_empty(cls, v: List[str]) -> List[str]:
        out = []
        for i, o in enumerate(v):
            t = str(o).strip() if o is not None else ""
            if not t:
                raise ValueError(f"options[{i}] cannot be empty")
            if len(t) > 2000:
                raise ValueError(f"options[{i}] is too long")
            out.append(t)
        return out


class SkillReadinessMultipleChoiceItem(SkillReadinessMcBase):
    question_type: Literal["multiple_choice"] = "multiple_choice"


class SkillReadinessScenarioItem(SkillReadinessMcBase):
    question_type: Literal["scenario"] = "scenario"


class SkillReadinessCodeMcqItem(SkillReadinessMcBase):
    question_type: Literal["code_mcq"] = "code_mcq"


class AptitudeReadinessMultipleChoiceItem(SkillReadinessMcBase):
    question_type: Literal["multiple_choice"] = "multiple_choice"
    section: Literal["quantitative", "logical", "verbal"]
    difficulty: Literal["easy", "moderate", "tricky"] = Field(
        default="moderate",
        description="Placement-style difficulty: easy / moderate / tricky",
    )
    asked_in: str = Field(
        default="Common pattern",
        max_length=200,
        description="Company or pattern label (e.g. TCS, Infosys, Common pattern)",
    )
    why_students_fail: str = Field(
        default="Common mistakes under time pressure.",
        max_length=500,
        description="Short reason why students often miss this",
    )


SkillReadinessQuestionItem = Annotated[
    Union[
        SkillReadinessYesNoItem,
        SkillReadinessMultipleChoiceItem,
        SkillReadinessScenarioItem,
        SkillReadinessCodeMcqItem,
    ],
    Field(discriminator="question_type"),
]


class PlanResponse(BaseModel):
    """Legacy plan: 15 Yes/No questions only."""

    evaluation_plan: List[LegacyPlanQuestionItem]


class SkillReadinessPlanResponse(BaseModel):
    """Rigorous skill-depth plan: yes_no, multiple_choice, scenario, code_mcq with explanations."""

    evaluation_plan: List[SkillReadinessQuestionItem]


class InterviewReadinessPlanResponse(BaseModel):
    """Holistic interview readiness: yes_no, multiple_choice, scenario, code_mcq with explanations."""

    evaluation_plan: List[SkillReadinessQuestionItem]


class AptitudeReadinessPlanResponse(BaseModel):
    """Aptitude readiness: 15 placement-style MCQs with strict section distribution."""

    evaluation_plan: List[AptitudeReadinessMultipleChoiceItem]


class EvaluateRequest(BaseModel):
    questions: List[str] = Field(..., min_length=1)
    answers: List[str] = Field(..., min_length=1)
    correct_answers: List[str] = Field(
        ...,
        min_length=1,
        description="Per question: Yes/No, or A–D for multiple_choice (same order as plan)",
    )
    study_topics: List[str] = Field(..., min_length=1, description="Study topic per question from Plan (for strengths/gaps/recommendations)")

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v: List[str]) -> List[str]:
        from app.schemas.answer_normalize import normalize_interview_answer

        normalized = []
        for i, ans in enumerate(v):
            try:
                normalized.append(normalize_interview_answer(ans))
            except ValueError as e:
                raise ValueError(f"answer at index {i}: {e}") from e
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
        from app.schemas.answer_normalize import normalize_interview_answer

        out = []
        for i, ans in enumerate(v):
            try:
                c = normalize_interview_answer(ans)
            except ValueError as e:
                raise ValueError(f"correct_answers[{i}]: {e}") from e
            if c not in VALID_EVAL_ANSWERS:
                raise ValueError(f"correct_answers[{i}] must be Yes, No, or A–D, got: {c!r}")
            out.append(c)
        return out

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