"""
Deterministic evaluation logic for Interview Readiness.
No LLM calls - purely rule-based scoring for consistency.
"""

from typing import List


class EvaluatorService:
    """Evaluates user answers and produces readiness score + learning roadmap."""

    async def evaluate_readiness(self, request) -> dict:
        total_questions = len(request.questions)
        if total_questions == 0:
            return {
                "readiness_percentage": 0,
                "readiness_label": "Not Ready",
                "strengths": [],
                "gaps": [],
                "learning_recommendations": [],
            }

        yes_answers = sum(1 for a in request.answers if a == "Yes")
        readiness_percentage = int((yes_answers / total_questions) * 100)

        if readiness_percentage < 50:
            readiness_label = "Not Ready"
        elif readiness_percentage < 80:
            readiness_label = "Almost Ready"
        else:
            readiness_label = "Interview Ready"

        strengths = [
            q for q, a in zip(request.questions, request.answers) if a == "Yes"
        ]
        gaps = [q for q, a in zip(request.questions, request.answers) if a == "No"]

        learning_recommendations = self._build_learning_roadmap(gaps)

        return {
            "readiness_percentage": readiness_percentage,
            "readiness_label": readiness_label,
            "strengths": strengths,
            "gaps": gaps,
            "learning_recommendations": learning_recommendations,
        }

    def _build_learning_roadmap(self, gaps: List[str]) -> List[dict]:
        """
        Prioritized roadmap: Critical, High, Medium, Optional.
        Deterministic logic based on keyword presence.
        """
        recommendations = []
        critical_keywords = {"core", "fundamental", "essential", "basic", "must"}
        high_keywords = {"design", "system", "architecture", "algorithm", "data"}
        medium_keywords = {"advanced", "optimization", "scaling", "testing"}

        for i, topic in enumerate(gaps):
            topic_lower = topic.lower()
            if any(kw in topic_lower for kw in critical_keywords):
                priority = "Critical"
                why = "Core topic essential for your target role."
            elif any(kw in topic_lower for kw in high_keywords):
                priority = "High"
                why = "Important for technical interviews."
            elif any(kw in topic_lower for kw in medium_keywords):
                priority = "Medium"
                why = "Would strengthen your profile."
            else:
                priority = "Optional"
                why = "Good to know for comprehensive preparation."

            recommendations.append({
                "priority": priority,
                "topic": topic,
                "why": why,
            })

        # Sort by priority order: Critical > High > Medium > Optional
        order = {"Critical": 0, "High": 1, "Medium": 2, "Optional": 3}
        recommendations.sort(key=lambda r: order.get(r["priority"], 4))

        return recommendations
