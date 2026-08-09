"""Updated question catalog with conversational, multi-part framing."""

from __future__ import annotations

from pydantic import BaseModel


class QuestionStep(BaseModel):
    key: str
    screen_title: str
    intro_text: str
    question_text: str
    response_type: str
    choices: list[dict] | None = None
    free_text_prompt: str | None = None
    free_text_placeholder: str | None = None
    follow_up_if: dict | None = None


KNOW_ME_QUESTIONS: list[QuestionStep] = [
    QuestionStep(
        key="placement_pressure",
        screen_title="Placement pressure",
        intro_text="When you think about placements, what comes to your mind first?",
        question_text="Select any that feel true:",
        response_type="multi_select",
        choices=[
            {"id": "dont_know_start", "label": "I don't know where to start"},
            {"id": "everyone_ahead", "label": "Everyone seems ahead of me"},
            {"id": "friends_better", "label": "My friends are preparing better than me"},
            {"id": "fear_not_placed", "label": "I'm scared I won't get placed"},
            {"id": "dont_know_expect", "label": "I don't know what companies expect"},
            {"id": "dont_know_skills", "label": "I don't know what skills I should learn"},
            {"id": "not_improving", "label": "I keep preparing but don't know if I'm improving"},
            {"id": "family_pressure", "label": "I'm worried about disappointing my family"},
        ],
        free_text_prompt="Tell me in your own words if you want.",
        free_text_placeholder="What's on your mind about placements?",
    ),
    QuestionStep(
        key="communication_fear",
        screen_title="Communication & speaking",
        intro_text="Imagine you're sitting in an interview tomorrow. Which part makes you uncomfortable?",
        question_text="Pick one or more:",
        response_type="multi_select",
        choices=[
            {"id": "introducing", "label": "Introducing myself"},
            {"id": "english", "label": "Speaking in English"},
            {"id": "find_words", "label": "Finding the right words"},
            {"id": "explain_project", "label": "Explaining my project"},
            {"id": "unexpected", "label": "Answering unexpected questions"},
            {"id": "confidently", "label": "Speaking confidently"},
            {"id": "hr_talk", "label": "Talking to HR"},
        ],
        free_text_prompt="What do you think the interviewer might think about you?",
        free_text_placeholder="I worry they might notice that I...",
    ),
    QuestionStep(
        key="technical_confidence",
        screen_title="Technical confidence",
        intro_text="Be completely honest — which statement feels closest to you?",
        question_text="Pick one:",
        response_type="single_select",
        choices=[
            {"id": "know_plan", "label": "I know what to study and I'm following a plan."},
            {"id": "some_things", "label": "I know some things, but my fundamentals aren't strong."},
            {"id": "many_topics", "label": "I've studied many topics but can't apply them."},
            {"id": "follow_solutions", "label": "I can solve problems when I see solutions, but struggle on my own."},
            {"id": "dont_know", "label": "I don't really know what I should be learning."},
            {"id": "unprepared", "label": "I feel technically unprepared."},
        ],
        free_text_prompt="What's the one technical thing you're most afraid you'll be asked?",
        free_text_placeholder="The thing I'm terrified of is...",
    ),
    QuestionStep(
        key="project_confidence",
        screen_title="Projects & depth",
        intro_text="If an interviewer asks 'Explain your project,' how comfortable are you?",
        question_text="Choose one:",
        response_type="single_select",
        choices=[
            {"id": "explain_all", "label": "😄 I can explain everything."},
            {"id": "explain_basics", "label": "🙂 I can explain the basics."},
            {"id": "know_not_depth", "label": "😐 I know the project but not the technical depth."},
            {"id": "followed_tutorials", "label": "😟 I mostly followed tutorials / someone else's work."},
            {"id": "afraid_questions", "label": "😰 I'm afraid they'll ask something I don't know."},
        ],
        free_text_prompt="If you could change one thing about your project preparation, what would it be?",
        free_text_placeholder="I wish I had...",
    ),
    QuestionStep(
        key="friend_comparison",
        screen_title="Friends & comparison",
        intro_text="When someone in your class gets placed before you, what do you usually feel?",
        question_text="Pick what feels true:",
        response_type="single_select",
        choices=[
            {"id": "genuinely_happy", "label": "I'm genuinely happy for them."},
            {"id": "start_comparing", "label": "I start comparing myself."},
            {"id": "wonder_why", "label": "I wonder what they're doing that I'm not."},
            {"id": "falling_behind", "label": "I feel like I'm falling behind."},
            {"id": "get_motivated", "label": "I get motivated."},
            {"id": "feel_anxious", "label": "I feel anxious about my own placement."},
        ],
        free_text_prompt="What do you wish you could tell yourself at that moment?",
        free_text_placeholder="I wish I could say to myself...",
    ),
    QuestionStep(
        key="family_support",
        screen_title="Home & family",
        intro_text="Is there any pressure outside college that affects how you think about placements?",
        question_text="You can select multiple or none:",
        response_type="multi_select",
        choices=[
            {"id": "family_expect", "label": "Family expectations"},
            {"id": "financial", "label": "Financial pressure"},
            {"id": "disappoint", "label": "Fear of disappointing someone"},
            {"id": "high_pay", "label": "Pressure to get a high-paying job"},
            {"id": "compare_relatives", "label": "Comparing myself with relatives/friends"},
            {"id": "no_pressure", "label": "No major outside pressure"},
            {"id": "prefer_not_say", "label": "Prefer not to say"},
        ],
        free_text_prompt="If you want, tell us more.",
        free_text_placeholder="The pressure I feel is...",
    ),
    QuestionStep(
        key="main_fear",
        screen_title="Your deepest question",
        intro_text="This is important.",
        question_text="What are you afraid to ask someone about placements?",
        response_type="free_text_only",
        free_text_placeholder=(
            "Examples: 'Is my coding good enough?' 'I copied my project.' "
            "'My English isn't good.' 'What if I don't get placed?'"
        ),
    ),
    QuestionStep(
        key="anything_else",
        screen_title="Your space",
        intro_text="Anything else?",
        question_text="This is your space. You can say something you haven't told anyone else about your placement preparation.",
        response_type="free_text_only",
        free_text_placeholder="I've been thinking about...",
    ),
]


def get_question_by_key(key: str) -> QuestionStep | None:
    for q in KNOW_ME_QUESTIONS:
        if q.key == key:
            return q
    return None


def question_keys() -> list[str]:
    return [q.key for q in KNOW_ME_QUESTIONS]
