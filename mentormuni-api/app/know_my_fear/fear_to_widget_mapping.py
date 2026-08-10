"""
Map placement fears to MentorMuni widgets & tools.
Instead of generic advice, solutions point to real features.
"""

from enum import Enum
from typing import Optional


class WidgetType(str, Enum):
    """Available MentorMuni tools/widgets."""
    
    # Interview & Communication
    AI_HR_MOCK = "ai_hr_mock"           # For communication/HR fears
    VOICE_INTERVIEW = "voice_interview"  # For speaking confidence
    
    # Skills & Technical
    SKILL_READINESS_TEST = "skill_readiness_test"  # Assessment
    SKILL_AI_MOCK = "skill_ai_mock"                # Practice
    CODING_ROUND = "coding_round"                  # Coding practice
    DSA_PRACTICE = "dsa_practice"                  # DSA problems
    
    # Projects & Portfolios
    PROJECT_AI_MOCK = "project_ai_mock"  # Explain projects
    PORTFOLIO_REVIEW = "portfolio_review" # Portfolio feedback
    
    # Aptitude
    APTITUDE_TEST = "aptitude_test"      # Aptitude readiness
    
    # General
    MOCK_INTERVIEW = "mock_interview"    # Full interview
    LEADERBOARD = "leaderboard"          # Comparison & motivation
    READINESS_ROADMAP = "readiness_roadmap"  # Learning path


class FearWidget:
    """Links a fear to specific widgets with context."""
    
    def __init__(
        self,
        fear_id: str,
        fear_name: str,
        primary_widget: WidgetType,
        secondary_widgets: list[WidgetType],
        context: dict,
        progression: list[dict],
    ):
        self.fear_id = fear_id
        self.fear_name = fear_name
        self.primary_widget = primary_widget
        self.secondary_widgets = secondary_widgets
        self.context = context  # Widget-specific config
        self.progression = progression  # Week-by-week usage


# ============================================================================
# COMMUNICATION FEARS
# ============================================================================

FEAR_ENGLISH_COMMUNICATION = FearWidget(
    fear_id="english_communication",
    fear_name="English Communication (Speaking, Confidence)",
    primary_widget=WidgetType.AI_HR_MOCK,
    secondary_widgets=[
        WidgetType.VOICE_INTERVIEW,
        WidgetType.MOCK_INTERVIEW,
    ],
    context={
        "ai_hr_mock": {
            "focus_areas": ["fluency", "clarity", "confidence"],
            "difficulty": "adaptive",  # Starts easy
            "interview_style": "conversational",  # Not formal
            "duration_minutes": 10,
            "frequency": "daily",
        },
        "voice_interview": {
            "focus": "real-time speaking",
            "topics": ["self-intro", "projects", "experience"],
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "AI HR Mock (5 min) - Self introduction & basic Q&A",
            "tool": WidgetType.AI_HR_MOCK,
            "metric": "clarity score, pauses, filler words",
            "target": "Comfortable speaking English",
        },
        {
            "week": 2,
            "activity": "Voice Interview (10 min) - Project explanation",
            "tool": WidgetType.VOICE_INTERVIEW,
            "metric": "fluency score, response quality",
            "target": "Explain projects confidently",
        },
        {
            "week": 3,
            "activity": "Mock Interview - Full interview",
            "tool": WidgetType.MOCK_INTERVIEW,
            "metric": "overall communication score",
            "target": "Interview ready",
        },
    ],
)


FEAR_HR_INTERVIEW = FearWidget(
    fear_id="hr_interview",
    fear_name="HR Interview (Soft Skills, Behavior)",
    primary_widget=WidgetType.AI_HR_MOCK,
    secondary_widgets=[
        WidgetType.MOCK_INTERVIEW,
        WidgetType.VOICE_INTERVIEW,
    ],
    context={
        "ai_hr_mock": {
            "interview_type": "hr_specific",
            "topics": ["tell_me_about_yourself", "strengths", "weaknesses",
                      "situation_handling", "team_experience"],
            "difficulty": "progressive",  # Gets harder
            "feedback": "detailed",  # Deep analysis
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "AI HR: Tell me about yourself",
            "tool": WidgetType.AI_HR_MOCK,
            "metric": "structure, confidence, clarity",
            "target": "Perfect 60-second intro",
        },
        {
            "week": 2,
            "activity": "AI HR: Behavioral questions (STAR method)",
            "tool": WidgetType.AI_HR_MOCK,
            "metric": "structure, relevance, impact",
            "target": "Master STAR framework",
        },
        {
            "week": 3,
            "activity": "Full Mock Interview with HR focus",
            "tool": WidgetType.MOCK_INTERVIEW,
            "metric": "overall performance",
            "target": "Pass HR round confidently",
        },
    ],
)


# ============================================================================
# TECHNICAL FEARS
# ============================================================================

FEAR_DSA_WEAK = FearWidget(
    fear_id="dsa_weak",
    fear_name="DSA Not Strong (Data Structures & Algorithms)",
    primary_widget=WidgetType.DSA_PRACTICE,
    secondary_widgets=[
        WidgetType.CODING_ROUND,
        WidgetType.SKILL_READINESS_TEST,
        WidgetType.SKILL_AI_MOCK,
    ],
    context={
        "dsa_practice": {
            "start_level": "basics",  # Array, LinkedList, Stack
            "progression": "gradual",
            "problem_types": ["easy", "medium"],
            "focus": "fundamentals first",
        },
        "coding_round": {
            "difficulty": "adaptive",
            "start_with": "basic_arrays_strings",
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "DSA Fundamentals: Arrays, Strings, Basics",
            "tool": WidgetType.DSA_PRACTICE,
            "metric": "10 easy problems solved",
            "target": "Strong fundamentals",
        },
        {
            "week": 2,
            "activity": "DSA: LinkedList, Stack, Queue",
            "tool": WidgetType.DSA_PRACTICE,
            "metric": "15 problems, 80%+ accuracy",
            "target": "Data structures mastery",
        },
        {
            "week": 3,
            "activity": "Coding Round: Easy coding problems",
            "tool": WidgetType.CODING_ROUND,
            "metric": "solve 3 problems in 30 mins",
            "target": "Interview-ready DSA",
        },
    ],
)


FEAR_SPECIFIC_SKILL = FearWidget(
    fear_id="specific_skill_weak",
    fear_name="Specific Skill Weak (Java, Python, React, etc.)",
    primary_widget=WidgetType.SKILL_READINESS_TEST,
    secondary_widgets=[
        WidgetType.SKILL_AI_MOCK,
        WidgetType.CODING_ROUND,
        WidgetType.READINESS_ROADMAP,
    ],
    context={
        "skill_readiness_test": {
            "identify": "knowledge gaps",
            "diagnose": "specific weak areas",
        },
        "skill_ai_mock": {
            "target_skill": "dynamic",  # Based on test results
            "practice_type": "concepts_then_code",
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "Skill Readiness Test: Diagnose gaps",
            "tool": WidgetType.SKILL_READINESS_TEST,
            "metric": "identify top 3 weak areas",
            "target": "Know what to fix",
        },
        {
            "week": 2,
            "activity": "Skill AI Mock: Practice weak concepts",
            "tool": WidgetType.SKILL_AI_MOCK,
            "metric": "score 70%+ on practice",
            "target": "Concept mastery",
        },
        {
            "week": 3,
            "activity": "Coding Round: Apply in interviews",
            "tool": WidgetType.CODING_ROUND,
            "metric": "solve 2+ problems",
            "target": "Interview ready",
        },
    ],
)


FEAR_CODING_WEAK = FearWidget(
    fear_id="coding_weak",
    fear_name="Coding Skills Weak (Can't write code)",
    primary_widget=WidgetType.CODING_ROUND,
    secondary_widgets=[
        WidgetType.DSA_PRACTICE,
        WidgetType.SKILL_AI_MOCK,
    ],
    context={
        "coding_round": {
            "start_level": "very_basic",  # Hello world level
            "progression": "linear",
            "problems": ["easy", "easy", "easy", "medium"],
            "time_limit": "relaxed",  # More time initially
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "Coding: Start very basic (loops, functions)",
            "tool": WidgetType.CODING_ROUND,
            "metric": "solve 5 basic problems",
            "target": "Comfortable writing code",
        },
        {
            "week": 2,
            "activity": "Coding: Medium problems, build confidence",
            "tool": WidgetType.CODING_ROUND,
            "metric": "solve 4 medium problems",
            "target": "Can solve interview problems",
        },
        {
            "week": 3,
            "activity": "DSA + Coding combined practice",
            "tool": WidgetType.DSA_PRACTICE,
            "metric": "solve 10 problems mixed",
            "target": "Interview ready",
        },
    ],
)


# ============================================================================
# PROJECT & PORTFOLIO FEARS
# ============================================================================

FEAR_PROJECT_EXPLANATION = FearWidget(
    fear_id="project_explanation",
    fear_name="Can't Explain Projects (Technical Depth)",
    primary_widget=WidgetType.PROJECT_AI_MOCK,
    secondary_widgets=[
        WidgetType.VOICE_INTERVIEW,
        WidgetType.MOCK_INTERVIEW,
        WidgetType.PORTFOLIO_REVIEW,
    ],
    context={
        "project_ai_mock": {
            "focus": "technical_depth",
            "feedback": "detailed explanation quality",
            "metrics": ["clarity", "depth", "completeness"],
        },
        "voice_interview": {
            "focus": "verbal project explanation",
            "time_limit": "5_minutes",
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "Project AI Mock: Explain architecture",
            "tool": WidgetType.PROJECT_AI_MOCK,
            "metric": "clarity score 70%+",
            "target": "Understand own project deeply",
        },
        {
            "week": 2,
            "activity": "Voice Interview: 5-min project pitch",
            "tool": WidgetType.VOICE_INTERVIEW,
            "metric": "record 3 explanations, improve flow",
            "target": "Fluent verbal explanation",
        },
        {
            "week": 3,
            "activity": "Full Mock Interview: Project questions",
            "tool": WidgetType.MOCK_INTERVIEW,
            "metric": "handle follow-up questions",
            "target": "Interview ready on projects",
        },
    ],
)


FEAR_NO_PROJECTS = FearWidget(
    fear_id="no_projects",
    fear_name="No Real Projects (Portfolio Gap)",
    primary_widget=WidgetType.PORTFOLIO_REVIEW,
    secondary_widgets=[
        WidgetType.PROJECT_AI_MOCK,
        WidgetType.READINESS_ROADMAP,
    ],
    context={
        "portfolio_review": {
            "action": "build_quick_project",
            "timeline": "2_weeks",
            "project_ideas": "beginner_friendly",
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "Portfolio Review: Plan quick project",
            "tool": WidgetType.PORTFOLIO_REVIEW,
            "metric": "finalize project idea",
            "target": "Have project plan",
        },
        {
            "week": 2,
            "activity": "Build basic project (TODO app, blog, etc.)",
            "tool": WidgetType.READINESS_ROADMAP,
            "metric": "complete working project",
            "target": "Have something to show",
        },
        {
            "week": 3,
            "activity": "Project AI Mock: Practice explanation",
            "tool": WidgetType.PROJECT_AI_MOCK,
            "metric": "explain confidently",
            "target": "Interview ready",
        },
    ],
)


# ============================================================================
# CONFIDENCE & APTITUDE FEARS
# ============================================================================

FEAR_APTITUDE_WEAK = FearWidget(
    fear_id="aptitude_weak",
    fear_name="Aptitude Not Strong (Quant, Logical, Verbal)",
    primary_widget=WidgetType.APTITUDE_TEST,
    secondary_widgets=[
        WidgetType.READINESS_ROADMAP,
    ],
    context={
        "aptitude_test": {
            "adaptive": True,  # Adjusts difficulty
            "categories": ["quantitative", "logical", "verbal"],
            "weekly_practice": "20_questions",
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "Aptitude Test: Identify weak areas",
            "tool": WidgetType.APTITUDE_TEST,
            "metric": "diagnostic, 60%+ score",
            "target": "Know what to improve",
        },
        {
            "week": 2,
            "activity": "Aptitude Practice: Focus on weak category",
            "tool": WidgetType.APTITUDE_TEST,
            "metric": "20 problems daily, 70%+ accuracy",
            "target": "Category mastery",
        },
        {
            "week": 3,
            "activity": "Full Aptitude Test: Validate improvement",
            "tool": WidgetType.APTITUDE_TEST,
            "metric": "80%+ score",
            "target": "Aptitude ready",
        },
    ],
)


FEAR_PLACEMENT_CONFIDENCE = FearWidget(
    fear_id="placement_confidence",
    fear_name="General Placement Confidence (Imposter Syndrome)",
    primary_widget=WidgetType.MOCK_INTERVIEW,
    secondary_widgets=[
        WidgetType.LEADERBOARD,
        WidgetType.READINESS_ROADMAP,
        WidgetType.VOICE_INTERVIEW,
    ],
    context={
        "mock_interview": {
            "type": "full_round",
            "feedback": "encouraging_and_detailed",
            "confidence_building": True,
        },
    },
    progression=[
        {
            "week": 1,
            "activity": "Mock Interview: Full interview (low pressure)",
            "tool": WidgetType.MOCK_INTERVIEW,
            "metric": "complete without panic",
            "target": "Realize you can do this",
        },
        {
            "week": 2,
            "activity": "Readiness Roadmap: Understand progress",
            "tool": WidgetType.READINESS_ROADMAP,
            "metric": "see 70%+ overall readiness",
            "target": "Build confidence via data",
        },
        {
            "week": 3,
            "activity": "Mock Interview #2: More challenging",
            "tool": WidgetType.MOCK_INTERVIEW,
            "metric": "higher score than week 1",
            "target": "See tangible improvement",
        },
    ],
)


# ============================================================================
# MAPPING FUNCTION
# ============================================================================

FEAR_TO_WIDGET_MAP = {
    # Communication fears
    "english_communication": FEAR_ENGLISH_COMMUNICATION,
    "hr_interview": FEAR_HR_INTERVIEW,
    "speaking_confidence": FEAR_ENGLISH_COMMUNICATION,
    "communication_weak": FEAR_ENGLISH_COMMUNICATION,
    
    # Technical fears
    "dsa_weak": FEAR_DSA_WEAK,
    "dsa_not_strong": FEAR_DSA_WEAK,
    "specific_skill": FEAR_SPECIFIC_SKILL,
    "java_weak": FEAR_SPECIFIC_SKILL,
    "python_weak": FEAR_SPECIFIC_SKILL,
    "react_weak": FEAR_SPECIFIC_SKILL,
    "coding_weak": FEAR_CODING_WEAK,
    "cant_write_code": FEAR_CODING_WEAK,
    
    # Project fears
    "project_explanation": FEAR_PROJECT_EXPLANATION,
    "cant_explain_projects": FEAR_PROJECT_EXPLANATION,
    "no_projects": FEAR_NO_PROJECTS,
    "portfolio_gap": FEAR_NO_PROJECTS,
    
    # Confidence fears
    "aptitude_weak": FEAR_APTITUDE_WEAK,
    "placement_confidence": FEAR_PLACEMENT_CONFIDENCE,
    "imposter_syndrome": FEAR_PLACEMENT_CONFIDENCE,
}


def get_widget_for_fear(fear_name: str) -> Optional[FearWidget]:
    """Look up widget mapping for a fear."""
    fear_key = fear_name.lower().replace(" ", "_")
    return FEAR_TO_WIDGET_MAP.get(fear_key)


def get_all_fear_mappings() -> dict:
    """Return all fear to widget mappings."""
    return FEAR_TO_WIDGET_MAP


def build_fear_widget_context(fear_widget: FearWidget) -> dict:
    """Build the context for OpenAI to reference the widget."""
    return {
        "fear_id": fear_widget.fear_id,
        "fear_name": fear_widget.fear_name,
        "primary_tool": fear_widget.primary_widget.value,
        "secondary_tools": [w.value for w in fear_widget.secondary_widgets],
        "tool_contexts": fear_widget.context,
        "progression": fear_widget.progression,
    }
