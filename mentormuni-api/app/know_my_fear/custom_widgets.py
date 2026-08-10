"""
Custom widgets for fears that don't have existing MentorMuni tools.
These are suggestions for new features to build based on student needs.
"""

from enum import Enum
from typing import Optional


class CustomWidgetType(str, Enum):
    """Custom widgets that can be created on-demand."""
    
    # Communication & Confidence
    CONFIDENCE_JOURNAL = "confidence_journal"          # Daily journaling
    PEER_FEEDBACK_LOOP = "peer_feedback_loop"          # Get feedback from peers
    MENTOR_MATCHING = "mentor_matching"                # One-on-one mentor
    SPEECH_COACH_AI = "speech_coach_ai"                # AI speech coaching
    
    # Technical
    CONCEPT_BREAKDOWN = "concept_breakdown"            # Break down complex concepts
    VISUAL_LEARNING = "visual_learning"                # Visualize algorithms/concepts
    QUICK_REFERENCE = "quick_reference"                # Cheat sheets, quick guides
    
    # Projects & Portfolio
    PROJECT_SHOWCASE = "project_showcase"              # Build and showcase projects
    GITHUB_ANALYZER = "github_analyzer"                # Analyze GitHub profile
    PROJECT_IDEA_GENERATOR = "project_idea_generator"  # Suggest beginner projects
    
    # Wellness & Stress
    STRESS_MANAGEMENT = "stress_management"            # Meditation, breathing
    MOTIVATION_TRACKER = "motivation_tracker"          # Track motivation levels
    FEAR_JOURNAL = "fear_journal"                      # Track fear progress
    
    # Group & Social
    STUDY_GROUP_FINDER = "study_group_finder"          # Find study buddies
    PEER_COMPETITION = "peer_competition"              # Friendly competition
    SUCCESS_STORIES = "success_stories"                # Learn from others
    
    # General
    DAILY_HABIT_TRACKER = "daily_habit_tracker"        # Track daily activities
    ACHIEVEMENT_BADGES = "achievement_badges"         # Gamification


class CustomWidget:
    """Represents a custom widget that can be created."""
    
    def __init__(
        self,
        widget_id: str,
        name: str,
        description: str,
        purpose: str,
        how_it_works: str,
        weekly_time: int,  # Minutes per week
        difficulty: str,  # easy, medium, hard
        fear_types: list[str],  # Which fears it helps with
        benefits: list[str],
        status: str,  # "existing", "suggested", "in_development"
    ):
        self.widget_id = widget_id
        self.name = name
        self.description = description
        self.purpose = purpose
        self.how_it_works = how_it_works
        self.weekly_time = weekly_time
        self.difficulty = difficulty
        self.fear_types = fear_types
        self.benefits = benefits
        self.status = status


# ============================================================================
# COMMUNICATION & CONFIDENCE CUSTOM WIDGETS
# ============================================================================

WIDGET_CONFIDENCE_JOURNAL = CustomWidget(
    widget_id="confidence_journal",
    name="Daily Confidence Journal",
    description="Private journaling to track and build confidence",
    purpose="Build self-awareness and track emotional growth",
    how_it_works="""
    Each day, student writes:
    - What I accomplished today
    - One thing I'm proud of
    - One thing I'm improving on
    - How confident I feel (1-10)
    
    AI analyzes patterns and provides insights.
    """,
    weekly_time=35,  # 5 minutes daily
    difficulty="easy",
    fear_types=["confidence", "imposter_syndrome", "self_doubt"],
    benefits=[
        "Recognizes daily progress",
        "Builds confidence through awareness",
        "Identifies improvement patterns",
        "Personal growth tracking",
    ],
    status="suggested",
)


WIDGET_PEER_FEEDBACK = CustomWidget(
    widget_id="peer_feedback_loop",
    name="Peer Feedback Exchange",
    description="Get constructive feedback from peers",
    purpose="Learn from others and improve communication",
    how_it_works="""
    1. Student submits a recording (voice/video) of themselves
    2. AI provides initial feedback
    3. Peers can optionally provide feedback (peer review)
    4. Student reflects on feedback
    5. Can resubmit and see improvement
    """,
    weekly_time=60,  # 1 hour per week
    difficulty="medium",
    fear_types=["communication", "english", "project_explanation"],
    benefits=[
        "Real human feedback (not just AI)",
        "See different perspectives",
        "Build relationships",
        "Improve through peer learning",
    ],
    status="suggested",
)


WIDGET_MENTOR_MATCHING = CustomWidget(
    widget_id="mentor_matching",
    name="AI Mentor Matching & 1-on-1",
    description="One-on-one mentoring from experienced professionals",
    purpose="Get personalized guidance from someone who's been there",
    how_it_works="""
    1. Student is matched with a mentor based on their fears
    2. Weekly 30-minute calls (scheduled)
    3. Mentor guides them through the 6-week journey
    4. Mentor reviews progress weekly
    5. Mentor provides accountability & support
    """,
    weekly_time=30,  # 30 min/week
    difficulty="medium",
    fear_types=["confidence", "interview", "all"],
    benefits=[
        "Personal accountability",
        "Experience-based guidance",
        "Motivation from mentor",
        "Network building",
    ],
    status="suggested",
)


WIDGET_SPEECH_COACH_AI = CustomWidget(
    widget_id="speech_coach_ai",
    name="AI Speech Coach",
    description="Real-time speech coaching with instant feedback",
    purpose="Improve speaking skills with detailed audio analysis",
    how_it_works="""
    1. Student speaks (answer given question or free speech)
    2. AI analyzes:
       - Pace (too fast/slow)
       - Pauses and filler words (um, uh, like)
       - Intonation and confidence
       - Clarity and pronunciation
    3. Real-time coaching feedback
    4. Suggestions for improvement
    5. Replay and compare with previous attempts
    """,
    weekly_time=45,  # 3 x 15 min sessions
    difficulty="easy",
    fear_types=["communication", "english", "interview", "hr"],
    benefits=[
        "Real-time feedback",
        "Detailed audio analysis",
        "See progress visually",
        "Confidence building",
    ],
    status="suggested",
)


# ============================================================================
# TECHNICAL & LEARNING CUSTOM WIDGETS
# ============================================================================

WIDGET_CONCEPT_BREAKDOWN = CustomWidget(
    widget_id="concept_breakdown",
    name="Concept Breakdown AI",
    description="AI breaks down complex concepts into simple steps",
    purpose="Understand difficult technical concepts",
    how_it_works="""
    1. Student says: "Explain binary trees"
    2. AI breaks it down into layers:
       - Level 1: What is it? (simple explanation)
       - Level 2: Why does it matter?
       - Level 3: How do you use it?
       - Level 4: Interview questions
    3. Student can ask follow-up questions
    4. Interactive learning with visualizations
    """,
    weekly_time=90,  # 1.5 hours per week
    difficulty="medium",
    fear_types=["dsa", "technical", "coding"],
    benefits=[
        "Complex concepts become simple",
        "Learn at your own pace",
        "Multiple explanations",
        "Interview-ready understanding",
    ],
    status="suggested",
)


WIDGET_VISUAL_LEARNING = CustomWidget(
    widget_id="visual_learning",
    name="Visual Algorithm Playground",
    description="See algorithms and data structures in action",
    purpose="Understand through visualization",
    how_it_works="""
    1. Student selects a data structure or algorithm
    2. Visual animation shows how it works
    3. Step-by-step explanation as it runs
    4. Can input own data and see it execute
    5. Compare different approaches visually
    """,
    weekly_time=60,  # 1 hour per week
    difficulty="easy",
    fear_types=["dsa", "technical", "visual_learners"],
    benefits=[
        "See, don't just read",
        "Intuitive understanding",
        "Less intimidating",
        "Retention improves",
    ],
    status="suggested",
)


WIDGET_QUICK_REFERENCE = CustomWidget(
    widget_id="quick_reference",
    name="Personalized Quick Reference Guides",
    description="AI-generated cheat sheets for what you need",
    purpose="Quick access to important concepts",
    how_it_works="""
    1. AI generates personalized cheat sheets
    2. Based on:
       - Your weak areas (from tests)
       - Your specific fear (what's being asked)
       - Common interview questions
    3. 1-page reference for quick review
    4. Organized and visually clear
    5. Can be printed or digital
    """,
    weekly_time=20,  # Reference, not active learning
    difficulty="easy",
    fear_types=["technical", "dsa", "interview"],
    benefits=[
        "Quick refresher before interview",
        "Organized knowledge",
        "Less time reviewing",
        "More confidence",
    ],
    status="suggested",
)


# ============================================================================
# PROJECT & PORTFOLIO CUSTOM WIDGETS
# ============================================================================

WIDGET_PROJECT_SHOWCASE = CustomWidget(
    widget_id="project_showcase",
    name="Project Showcase & Gallery",
    description="Build and showcase projects with peer feedback",
    purpose="Have something impressive to show in interviews",
    how_it_works="""
    1. AI suggests beginner-friendly projects
    2. Step-by-step guides to build them
    3. Student builds and submits
    4. AI reviews code quality
    5. Project displayed in portfolio
    6. Peers can rate and comment
    """,
    weekly_time=180,  # 3 hours per week (project work)
    difficulty="hard",
    fear_types=["no_projects", "portfolio_gap", "project_explanation"],
    benefits=[
        "Tangible portfolio items",
        "Real learning through building",
        "Social proof (peer ratings)",
        "Confidence in interviews",
    ],
    status="suggested",
)


WIDGET_GITHUB_ANALYZER = CustomWidget(
    widget_id="github_analyzer",
    name="GitHub Profile Analyzer",
    description="AI analyzes and improves your GitHub profile",
    purpose="Make your GitHub profile interview-ready",
    how_it_works="""
    1. Connect GitHub profile
    2. AI analyzes:
       - Code quality
       - Contribution history
       - Project descriptions
       - Readability of README
    3. Generates improvement suggestions
    4. Rates profile (1-10)
    5. Shows what recruiters see
    """,
    weekly_time=60,  # Initial 1 hour, then ongoing
    difficulty="medium",
    fear_types=["portfolio_gap", "no_projects", "confidence"],
    benefits=[
        "Professional profile",
        "Recruiter-ready",
        "Code quality improvement",
        "Visibility increase",
    ],
    status="suggested",
)


WIDGET_PROJECT_IDEA_GENERATOR = CustomWidget(
    widget_id="project_idea_generator",
    name="AI Project Idea Generator",
    description="Get personalized beginner project ideas",
    purpose="Know exactly what projects to build",
    how_it_works="""
    1. AI asks about interests and skills
    2. Generates 5 project ideas (beginner-friendly)
    3. For each idea:
       - What you'll learn
       - Skills demonstrated
       - Estimated time
       - Step-by-step guide
       - Interview talking points
    4. Student picks one and starts building
    """,
    weekly_time=40,  # Initial brainstorm + reference
    difficulty="easy",
    fear_types=["no_projects", "portfolio_gap", "direction"],
    benefits=[
        "No more 'what should I build?'",
        "Aligned with interests",
        "Interview-ready projects",
        "Confidence in direction",
    ],
    status="suggested",
)


# ============================================================================
# WELLNESS & MOTIVATION CUSTOM WIDGETS
# ============================================================================

WIDGET_STRESS_MANAGEMENT = CustomWidget(
    widget_id="stress_management",
    name="Stress Management & Wellness",
    description="Tools to manage stress and anxiety",
    purpose="Stay mentally healthy during the 6-week journey",
    how_it_works="""
    1. Guided breathing exercises (2-5 min)
    2. Meditation for placement anxiety
    3. Progressive muscle relaxation
    4. Visualization techniques
    5. Stress level tracker
    """,
    weekly_time=30,  # Optional but recommended
    difficulty="easy",
    fear_types=["confidence", "stress", "all"],
    benefits=[
        "Reduced anxiety",
        "Better sleep",
        "Improved focus",
        "Emotional resilience",
    ],
    status="suggested",
)


WIDGET_MOTIVATION_TRACKER = CustomWidget(
    widget_id="motivation_tracker",
    name="Motivation & Momentum Tracker",
    description="Track and maintain motivation over 6 weeks",
    purpose="Stay motivated through the entire journey",
    how_it_works="""
    1. Daily motivation check-in (2 questions)
    2. Visual chart of motivation over time
    3. AI detects motivation dips
    4. Sends encouragement messages
    5. Celebrates wins and milestones
    """,
    weekly_time=10,  # 2 min daily
    difficulty="easy",
    fear_types=["confidence", "all"],
    benefits=[
        "Stay motivated 6 weeks",
        "Identify low points early",
        "Get encouragement exactly when needed",
        "Positive momentum",
    ],
    status="suggested",
)


# ============================================================================
# COMMUNITY & SOCIAL CUSTOM WIDGETS
# ============================================================================

WIDGET_STUDY_GROUP_FINDER = CustomWidget(
    widget_id="study_group_finder",
    name="Study Group Finder",
    description="Find and join study groups based on fears",
    purpose="Learn together with peers facing similar fears",
    how_it_works="""
    1. Students with similar fears matched
    2. Can form study groups (2-4 people)
    3. Schedule group study sessions
    4. Share resources and progress
    5. Accountability partner system
    """,
    weekly_time=120,  # 2 hours per week
    difficulty="easy",
    fear_types=["all"],
    benefits=[
        "Shared learning",
        "Accountability",
        "Social connection",
        "Motivation from others",
    ],
    status="suggested",
)


WIDGET_SUCCESS_STORIES = CustomWidget(
    widget_id="success_stories",
    name="Success Stories & Case Studies",
    description="Learn from students who conquered their fears",
    purpose="See proof that this works and get inspired",
    how_it_works="""
    1. Watch video/read story of student who had same fear
    2. See their journey: fear → solution → success
    3. Their exact 6-week timeline
    4. What worked for them
    5. Their tips and advice
    """,
    weekly_time=30,  # Optional inspiration
    difficulty="easy",
    fear_types=["confidence", "motivation"],
    benefits=[
        "Proof it's possible",
        "Inspiration and motivation",
        "Real-world examples",
        "Psychological safety",
    ],
    status="suggested",
)


# ============================================================================
# GENERAL GAMIFICATION CUSTOM WIDGETS
# ============================================================================

WIDGET_DAILY_HABIT_TRACKER = CustomWidget(
    widget_id="daily_habit_tracker",
    name="Daily Habit Tracker",
    description="Track daily activities for the 6 weeks",
    purpose="Build consistency and discipline",
    how_it_works="""
    1. Check off daily activities
    2. See streak counter (days in a row)
    3. Visual progress chart
    4. Weekly summary reports
    5. Celebrate consistency milestones
    """,
    weekly_time=5,  # Just tracking
    difficulty="easy",
    fear_types=["all"],
    benefits=[
        "Build consistency",
        "See progress visually",
        "Motivation through streaks",
        "Accountability",
    ],
    status="suggested",
)


WIDGET_ACHIEVEMENT_BADGES = CustomWidget(
    widget_id="achievement_badges",
    name="Achievement Badges & Gamification",
    description="Earn badges for milestones and achievements",
    purpose="Make the journey fun and rewarding",
    how_it_works="""
    1. Complete challenges → earn badges
    2. Badge examples:
       - First 5 minutes of speaking practice
       - Solve 10 coding problems
       - Complete a full mock interview
       - 7-day streak
       - Fear reduced by 50%
    3. Badges displayed in profile
    4. Share on social media
    5. Leaderboard for friendly competition
    """,
    weekly_time=5,  # Just gamification
    difficulty="easy",
    fear_types=["all"],
    benefits=[
        "Intrinsic motivation",
        "Celebrate progress",
        "Fun experience",
        "Social sharing",
    ],
    status="suggested",
)


# ============================================================================
# MAPPING
# ============================================================================

CUSTOM_WIDGETS_MAP = {
    # Communication
    "confidence_journal": WIDGET_CONFIDENCE_JOURNAL,
    "peer_feedback": WIDGET_PEER_FEEDBACK,
    "mentor_matching": WIDGET_MENTOR_MATCHING,
    "speech_coach": WIDGET_SPEECH_COACH_AI,
    
    # Technical
    "concept_breakdown": WIDGET_CONCEPT_BREAKDOWN,
    "visual_learning": WIDGET_VISUAL_LEARNING,
    "quick_reference": WIDGET_QUICK_REFERENCE,
    
    # Projects
    "project_showcase": WIDGET_PROJECT_SHOWCASE,
    "github_analyzer": WIDGET_GITHUB_ANALYZER,
    "project_ideas": WIDGET_PROJECT_IDEA_GENERATOR,
    
    # Wellness
    "stress_management": WIDGET_STRESS_MANAGEMENT,
    "motivation_tracker": WIDGET_MOTIVATION_TRACKER,
    
    # Community
    "study_groups": WIDGET_STUDY_GROUP_FINDER,
    "success_stories": WIDGET_SUCCESS_STORIES,
    
    # Gamification
    "habit_tracker": WIDGET_DAILY_HABIT_TRACKER,
    "achievement_badges": WIDGET_ACHIEVEMENT_BADGES,
}


def get_custom_widget(widget_id: str) -> Optional[CustomWidget]:
    """Get a custom widget by ID."""
    return CUSTOM_WIDGETS_MAP.get(widget_id)


def get_all_custom_widgets() -> dict:
    """Get all custom widgets."""
    return CUSTOM_WIDGETS_MAP


def get_custom_widgets_for_fear(fear_type: str) -> list[CustomWidget]:
    """Get all custom widgets that help with a specific fear."""
    widgets = []
    for widget in CUSTOM_WIDGETS_MAP.values():
        if fear_type.lower() in [f.lower() for f in widget.fear_types]:
            widgets.append(widget)
    return widgets
