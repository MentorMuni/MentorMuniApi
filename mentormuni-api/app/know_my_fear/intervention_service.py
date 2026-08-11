"""Service for 6-week Know Me intervention system."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.know_my_fear.intervention_prompt import (
    FEAR_SOLUTION_SYSTEM_PROMPT,
    WEEKLY_FEEDBACK_SYSTEM_PROMPT,
    FINAL_CELEBRATION_PROMPT,
    build_fear_solution_prompt,
    build_weekly_feedback_prompt,
    build_final_celebration_prompt,
)
from app.know_my_fear.constants import (
    PLAN_LOCK_DAYS,
    SCOREABLE_TOOLS,
    is_scoreable_tool,
    normalize_tool_code,
)
from app.know_my_fear.fear_to_widget_mapping import (
    get_widget_for_fear,
    build_fear_widget_context,
)
from app.know_my_fear.timeutil import utc_now
from app.models.private_checkin import PrivateStudentResponse
from app.models.private_intervention import (
    PrivateStudentFearSolution,
    PrivateStudentWeeklyProgress,
    PrivateStudentNotification,
    PrivateStudentMilestone,
    PrivateStudentInterventionStats,
    PrivateStudentPlanAction,
)
from app.models.user import User

logger = logging.getLogger(__name__)


class InterventionService:
    """Manage the 6-week fear resolution intervention."""

    def __init__(self):
        api_key = (settings.openai_api_key or "").strip() or None
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = settings.know_my_fear_model

    async def generate_fear_solutions(
        self,
        db: AsyncSession,
        checkin_id: int,
        student: User,
        fears: list[dict],
    ) -> list[dict]:
        """
        Generate 6-week action plans for each identified fear.
        Maps each fear to MentorMuni widgets/tools.
        
        Args:
            db: Database session
            checkin_id: Check-in ID
            student: Student user object
            fears: List of {name, severity, ...} dicts
            
        Returns:
            List of complete solution plans with widget references
        """
        solutions = []
        
        for fear in fears:
            logger.info(
                f"Generating solution for fear: {fear['name']} "
                f"(severity: {fear['severity']}/10)"
            )
            
            # Get widget mapping for this fear
            fear_widget = get_widget_for_fear(fear["name"])
            widget_context = {}
            
            if fear_widget:
                widget_context = build_fear_widget_context(fear_widget)
                logger.info(
                    f"✓ Found widget mapping: {fear_widget.primary_widget.value} "
                    f"(+ {len(fear_widget.secondary_widgets)} secondaries)"
                )
            else:
                logger.warning(f"No widget mapping found for: {fear['name']}")
            
            # Build context about student
            student_context = {
                "year": getattr(student, "batch_year", "Unknown"),
                "tech_skills": "Average",  # Could be enhanced with actual data
                "communication": "Average",
                "time_available": "2-3 hours/day",
                "learning_style": "Practical",
            }
            
            # Generate solution via OpenAI
            user_prompt = build_fear_solution_prompt(
                fear_name=fear["name"],
                severity=fear["severity"],
                student_context=student_context,
            )
            
            # Add widget context to prompt
            if widget_context:
                user_prompt += f"\n\nAvailable MentorMuni tools for this fear:\n{widget_context}"
            
            try:
                if not self.client:
                    raise RuntimeError("OpenAI API key not configured")
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": FEAR_SOLUTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                
                solution_text = response.choices[0].message.content.strip()
                solution_data = json.loads(solution_text)
                
                # Store in database
                initial = int(fear["severity"])
                solution = PrivateStudentFearSolution(
                    checkin_id=checkin_id,
                    student_id=student.id,
                    fear_id=fear.get("id", fear["name"].lower().replace(" ", "_")),
                    fear_name=fear["name"],
                    fear_severity=initial,
                    current_severity=initial,
                    solution_plan=solution_data,
                    weekly_actions=extract_weekly_actions(solution_data),
                    resources=solution_data.get("resources", []),
                )
                
                db.add(solution)
                await db.flush()
                
                solutions.append({
                    "solution_id": solution.id,
                    "fear_name": fear["name"],
                    "solution_data": solution_data,
                })
                
                logger.info(f"✓ Solution generated for {fear['name']}")
                
            except Exception as e:
                logger.error(f"Failed to generate solution for {fear['name']}: {e}")
                # Persist heuristic solution so status/weekly tracking still work
                heuristic = await self._heuristic_solution(fear)
                initial = int(fear["severity"])
                solution = PrivateStudentFearSolution(
                    checkin_id=checkin_id,
                    student_id=student.id,
                    fear_id=fear.get("id", fear["name"].lower().replace(" ", "_")),
                    fear_name=fear["name"],
                    fear_severity=initial,
                    current_severity=initial,
                    solution_plan=heuristic["solution_data"],
                    weekly_actions=extract_weekly_actions(heuristic["solution_data"]),
                    resources=heuristic["solution_data"].get("resources", []),
                )
                db.add(solution)
                await db.flush()
                solutions.append({
                    "solution_id": solution.id,
                    "fear_name": fear["name"],
                    "solution_data": heuristic["solution_data"],
                })
        
        return solutions

    async def generate_weekly_feedback(
        self,
        db: AsyncSession,
        student_id: int,
        fear_id: str,
        week_num: int,
        actions_completed: int,
        actions_total: int,
        self_assessment: float,
        severity_before: int,
        severity_after: int,
        challenges: Optional[str] = None,
    ) -> dict:
        """Generate personalized weekly feedback via OpenAI."""
        
        logger.info(f"Generating feedback for student {student_id}, week {week_num}")
        
        user_prompt = build_weekly_feedback_prompt(
            fear_name=fear_id,
            week_num=week_num,
            actions_completed=actions_completed,
            actions_total=actions_total,
            self_assessment=self_assessment,
            severity_before=severity_before,
            severity_after=severity_after,
            challenges=challenges,
        )
        
        try:
            if not self.client:
                return self._heuristic_feedback(week_num, severity_after)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": WEEKLY_FEEDBACK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            
            feedback_text = response.choices[0].message.content.strip()
            feedback_data = json.loads(feedback_text)
            
            return feedback_data
            
        except Exception as e:
            logger.error(f"Failed to generate feedback: {e}")
            return self._heuristic_feedback(week_num, severity_after)

    async def save_weekly_progress(
        self,
        db: AsyncSession,
        student_id: int,
        fear_id: str,
        week_num: int,
        actions_completed: int,
        actions_total: int,
        self_assessment: float,
        severity_before: int,
        severity_after: int,
        ai_feedback: dict,
        challenges: Optional[str] = None,
        commitment: Optional[str] = None,
        checkin_id: Optional[int] = None,
    ) -> None:
        """Save weekly progress to database."""
        
        progress = PrivateStudentWeeklyProgress(
            student_id=student_id,
            checkin_id=checkin_id,
            fear_id=fear_id,
            week_number=week_num,
            actions_completed=actions_completed,
            actions_total=actions_total,
            self_reported_improvement=self_assessment,
            ai_feedback=json.dumps(ai_feedback) if isinstance(ai_feedback, dict) else str(ai_feedback or ""),
            severity_before=severity_before,
            severity_after=severity_after,
            challenges=challenges,
            next_week_commitment=commitment,
        )
        
        db.add(progress)
        await db.flush()
        
        # Check for milestones
        await self._check_and_create_milestones(
            db, student_id, fear_id, week_num, severity_after
        )

    async def schedule_6_week_notifications(
        self,
        db: AsyncSession,
        student_id: int,
        checkin_id: int,
    ) -> None:
        """Schedule all 7 notifications for the 6-week journey."""
        
        notifications = [
            {
                "days": 0,
                "type": "start_week_1",
                "title": "Your Fear → Fearless Plan is Ready! 🚀",
                "message": "Check the personalized action plan we created just for you",
                "cta": "View Plan",
            },
            {
                "days": 3,
                "type": "mid_week_check",
                "title": "3-Day Check-in 📍",
                "message": "How's your first few days going? Quick update?",
                "cta": "Share Progress",
            },
            {
                "days": 7,
                "type": "weekly_review",
                "title": "You've Completed Week 1! 🎉",
                "message": "See how much you've improved this week",
                "cta": "View Results",
            },
            {
                "days": 14,
                "type": "weekly_review",
                "title": "Week 2 Check-in 📊",
                "message": "You're halfway through month 1! Keep the momentum!",
                "cta": "See Progress",
            },
            {
                "days": 21,
                "type": "milestone",
                "title": "3 Weeks Done! 🎯",
                "message": "You're 50% through. The hard part is behind you!",
                "cta": "Continue",
            },
            {
                "days": 28,
                "type": "weekly_review",
                "title": "Week 4 - Turning Point! 💪",
                "message": "You're almost there. Fear is melting away!",
                "cta": "Check Progress",
            },
            {
                "days": 42,
                "type": "weekly_review",
                "title": "Week 6 - Final Push! 🔥",
                "message": "Last week to eliminate this fear completely!",
                "cta": "Finish Strong",
            },
            {
                "days": 49,
                "type": "completion",
                "title": "You Conquered Your Fears! 🏆",
                "message": "All fears gone. You're ready for placement!",
                "cta": "See Summary",
            },
        ]
        
        # Idempotent: do not double-schedule for same check-in
        existing = await db.execute(
            select(PrivateStudentNotification.id).where(
                PrivateStudentNotification.checkin_id == checkin_id,
                PrivateStudentNotification.student_id == student_id,
            ).limit(1)
        )
        if existing.scalar():
            logger.info(f"Notifications already scheduled for checkin {checkin_id}")
            return
        
        start_date = utc_now()
        
        for notif in notifications:
            scheduled_date = start_date + timedelta(days=notif["days"])
            
            notification = PrivateStudentNotification(
                student_id=student_id,
                checkin_id=checkin_id,
                notification_type=notif["type"],
                scheduled_date=scheduled_date,
                title=notif["title"],
                message=notif["message"],
                cta_text=notif["cta"],
            )
            
            db.add(notification)
        
        await db.flush()
        logger.info(f"✓ Scheduled 8 notifications for student {student_id}")

    async def generate_final_celebration(
        self,
        db: AsyncSession,
        student_id: int,
        checkin_id: int,
        stats: dict,
    ) -> dict:
        """Generate final celebration message when all fears are conquered."""
        
        logger.info(f"Generating final celebration for student {student_id}")
        
        user_prompt = build_final_celebration_prompt(stats)
        
        try:
            if not self.client:
                return self._heuristic_celebration(stats)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": FINAL_CELEBRATION_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            
            celebration_text = response.choices[0].message.content.strip()
            celebration_data = json.loads(celebration_text)
            
            return celebration_data
            
        except Exception as e:
            logger.error(f"Failed to generate celebration: {e}")
            return self._heuristic_celebration(stats)

    async def _check_and_create_milestones(
        self,
        db: AsyncSession,
        student_id: int,
        fear_id: str,
        week_num: int,
        severity_after: int,
    ) -> None:
        """Create milestone records for achievement."""
        
        milestones = []
        
        # Fear reduced to 50%
        if severity_after <= 5:
            existing = await db.execute(
                select(PrivateStudentMilestone).where(
                    PrivateStudentMilestone.student_id == student_id,
                    PrivateStudentMilestone.fear_id == fear_id,
                    PrivateStudentMilestone.milestone_type == "fear_reduced_to_50",
                )
            )
            if not existing.scalar():
                milestones.append(
                    PrivateStudentMilestone(
                        student_id=student_id,
                        fear_id=fear_id,
                        milestone_type="fear_reduced_to_50",
                        achieved_week=week_num,
                        severity_reduced_to=severity_after,
                        celebration_message=f"Halfway there! Fear reduced from ~{severity_after + 5} to {severity_after}! 🎯",
                        extra_data={"previous": severity_after + 5, "current": severity_after},
                    )
                )
        
        # Fear conquered (0)
        if severity_after == 0:
            milestones.append(
                PrivateStudentMilestone(
                    student_id=student_id,
                    fear_id=fear_id,
                    milestone_type="fear_conquered",
                    achieved_week=week_num,
                    severity_reduced_to=0,
                    celebration_message=f"🏆 FEAR CONQUERED! You eliminated this fear completely in {week_num} weeks!",
                    extra_data={"fear": fear_id, "weeks_taken": week_num},
                )
            )
        
        for milestone in milestones:
            db.add(milestone)
        
        if milestones:
            await db.flush()
            logger.info(f"✓ Created {len(milestones)} milestones for {fear_id}")

    # Heuristic fallbacks
    async def _heuristic_solution(self, fear: dict) -> dict:
        """Fallback plan if OpenAI fails — still student-actionable."""

        fear_name = fear.get("name", "Unknown")
        key = str(fear_name).lower()

        if any(w in key for w in ("cod", "dsa", "leetcode")):
            week1 = {
                "theme": "Make coding feel smaller",
                "introduction": "One honest problem a day beats binge-watching solutions.",
                "weekly_metric": "You can explain one problem you solved yourself",
                "day1": {"action": "Try 1 easy Coding Round problem without opening a solution first.", "tool": "coding", "metric": "You attempted it yourself"},
                "day2": {"action": "Re-solve yesterday’s problem out loud.", "tool": "coding", "metric": "60-second approach"},
                "day3": {"action": "15-minute Practice drill on the topic that blocked you.", "tool": "practice", "metric": "One concept clearer"},
                "day4": {"action": "Write 4 lines: problem, approach, bug, next step.", "tool": "home", "metric": "A note you can reuse"},
                "day5": {"action": "Ask AI Mentor to grill you on that same problem.", "tool": "mentor", "metric": "You survive a follow-up"},
            }
        elif any(w in key for w in ("project", "explain")):
            week1 = {
                "theme": "Own your project story",
                "introduction": "They want one decision you owned — not a demo dump.",
                "weekly_metric": "A 90-second project story without notes",
                "day1": {"action": "Write problem → what you built → one hard decision → result.", "tool": "home", "metric": "Story fits one page"},
                "day2": {"action": "Run a Project mock and tell only that story.", "tool": "project_mock", "metric": "Under 2 minutes"},
                "day3": {"action": "Answer “why this approach?” with AI Mentor.", "tool": "mentor", "metric": "You have a real why"},
                "day4": {"action": "Record once, cut filler, do a shorter take.", "tool": "project_mock", "metric": "Second take is cleaner"},
                "day5": {"action": "Map the story to one company role.", "tool": "company_prep", "metric": "One company-specific sentence"},
            }
        elif any(w in key for w in ("english", "speak", "hr", "introduc", "communicat")):
            week1 = {
                "theme": "Warm up your voice",
                "introduction": "Speaking fear shrinks when the first 30 seconds feel familiar.",
                "weekly_metric": "A calm 30-second introduction",
                "day1": {"action": "Write a 4-line intro and say it without reading.", "tool": "home", "metric": "No script in hand"},
                "day2": {"action": "One AI HR mock — introduction only.", "tool": "hr_mock", "metric": "You finish without freezing"},
                "day3": {"action": "Repeat slower. Cut one filler word.", "tool": "hr_mock", "metric": "Fewer ums"},
                "day4": {"action": "AI Mentor asks “Tell me about yourself.” Answer again.", "tool": "mentor", "metric": "You recover if interrupted"},
                "day5": {"action": "Say the intro once as if a human is listening.", "tool": "home", "metric": "You did it"},
            }
        elif any(w in key for w in ("solution", "copy", "own")):
            week1 = {
                "theme": "Solve one thing yourself",
                "introduction": "One self-solved problem rebuilds trust in you.",
                "weekly_metric": "One problem you can teach without notes",
                "day1": {"action": "Hide solutions. Stay with one easy problem for 20 minutes.", "tool": "coding", "metric": "You stayed with it"},
                "day2": {"action": "Write the approach in plain English before code.", "tool": "home", "metric": "A 5-line plan"},
                "day3": {"action": "Code only from that plan.", "tool": "coding", "metric": "You know where you needed help"},
                "day4": {"action": "Teach the solution to AI Mentor.", "tool": "mentor", "metric": "They can follow you"},
                "day5": {"action": "Re-solve from scratch. No notes for 5 minutes.", "tool": "coding", "metric": "You remember the shape"},
            }
        else:
            week1 = {
                "theme": "One small proof you can move",
                "introduction": "Fear shrinks when you finish one visible thing.",
                "weekly_metric": "Three finished sessions you can point to",
                "day1": {"action": "Do the next 20-minute Home session. Stop when the timer ends.", "tool": "home", "metric": "You showed up"},
                "day2": {"action": "Tell AI Mentor what felt heavy. Ask for one drill only.", "tool": "mentor", "metric": "You named it"},
                "day3": {"action": "Do that one Practice drill. No second topic.", "tool": "practice", "metric": "You finished it"},
                "day4": {"action": "Write 3 lines: what you did, what was hard, what you’ll repeat.", "tool": "home", "metric": "A note exists"},
                "day5": {"action": "Repeat the same drill. Familiar is the point.", "tool": "practice", "metric": "It feels slightly less scary"},
            }

        return {
            "solution_id": None,
            "fear_name": fear_name,
            "solution_data": {
                "empathy_section": {
                    "what_i_hear": f"“{fear_name}” is a real placement weight — not a character flaw.",
                    "reframe": "We shrink it with one finished action at a time, not a 6-week fantasy.",
                    "reassurance": "You do not need to feel ready. You need a first proof.",
                },
                "action_plan_section": {"week1": week1},
                "week1": week1,
                "resources": [],
            },
        }

    def _heuristic_feedback(self, week_num: int, severity_after: int) -> dict:
        """Fallback feedback if OpenAI fails."""
        
        messages = {
            1: "Great start! You're building momentum.",
            2: "You're making real progress!",
            3: "Halfway there! You can do this!",
            4: "The hard part is behind you!",
            5: "Almost there! Final push!",
            6: "You did it! Fear is gone!",
        }
        
        return {
            "celebration": f"Great work this week!",
            "pattern_recognition": "You're showing consistent progress",
            "reframe": "Every action brings you closer to zero fear",
            "next_week_focus": "Keep the same momentum",
            "motivational_quote": messages.get(week_num, "You're doing great!"),
            "confidence_message": f"Fear is now at {severity_after}/10 - keep going!",
        }

    def _heuristic_celebration(self, stats: dict) -> dict:
        """Fallback celebration if OpenAI fails."""
        
        return {
            "celebration_title": "You Did It! 🎉",
            "main_message": f"You successfully conquered your fears! "
                          f"You completed {stats.get('actions_completed', 0)} actions "
                          f"and reduced your fear from {stats.get('initial_fear', 8)}/10 to 0/10!",
            "growth_recap": [
                f"Conquered {stats.get('fears_conquered', 0)} fears",
                f"Completed {stats.get('actions_completed', 0)} actions",
                f"Showed up for {stats.get('weeks_taken', 6)} weeks",
            ],
            "confidence_statement": "You have the skills. You have the confidence. You're ready!",
            "next_action": "Go apply to companies and get placed! 🚀",
        }

    # ------------------------------------------------------------------
    # Production helpers: severity, status, weekly submit, notifications
    # ------------------------------------------------------------------

    @staticmethod
    def compute_initial_fear_factor(responses: Optional[dict] = None) -> int:
        """0–10 starting fear factor from the check-in answers (never below 5)."""
        data = responses or {}
        score = 6
        pressure = list((data.get("placement_pressure") or {}).get("selected_ids") or [])
        comm = list((data.get("communication_fear") or {}).get("selected_ids") or [])
        tech = ((data.get("technical_confidence") or {}).get("selected_ids") or [None])[0]
        proj = ((data.get("project_confidence") or {}).get("selected_ids") or [None])[0]
        compare = ((data.get("friend_comparison") or {}).get("selected_ids") or [None])[0]
        if "fear_not_placed" in pressure:
            score += 2
        elif len(pressure) >= 3:
            score += 1
        if len(comm) >= 3:
            score += 1
        if tech in ("dont_know", "unprepared", "follow_solutions"):
            score += 1
        if proj in ("followed_tutorials", "know_not_depth", "afraid_questions"):
            score += 1
        if compare in ("falling_behind", "feel_anxious", "start_comparing"):
            score += 1
        return max(5, min(10, score))

    @staticmethod
    def fears_from_blockers(
        blockers: list,
        initial_severity: Optional[int] = None,
    ) -> list[dict]:
        """Map insight blockers → fear list for solution generation."""
        base = (
            max(5, min(10, int(initial_severity)))
            if initial_severity is not None
            else None
        )
        fears: list[dict] = []
        for i, blocker in enumerate(blockers[:3]):
            if isinstance(blocker, dict):
                title = (blocker.get("title") or f"Blocker {i + 1}").strip()
            else:
                title = (getattr(blocker, "title", None) or f"Blocker {i + 1}").strip()
            fear_id = (
                title.lower()
                .replace("'", "")
                .replace('"', "")
                .replace("/", " ")
                .replace("-", " ")
            )
            fear_id = "_".join(p for p in fear_id.split() if p)[:120] or f"fear_{i + 1}"
            if base is not None:
                severity = max(5, min(10, base - i))
            else:
                severity = max(5, min(10, 10 - i))
            fears.append({"id": fear_id, "name": title, "severity": severity})
        if not fears:
            fears.append(
                {
                    "id": "placement_confidence",
                    "name": "Placement confidence",
                    "severity": base if base is not None else 8,
                }
            )
        return fears

    async def ensure_solutions_for_checkin(
        self,
        db: AsyncSession,
        student: User,
        checkin_id: int,
        blockers: list,
        responses: Optional[dict] = None,
    ) -> list[dict]:
        """Generate solutions once per check-in (idempotent)."""
        existing = await db.execute(
            select(PrivateStudentFearSolution).where(
                PrivateStudentFearSolution.checkin_id == checkin_id,
                PrivateStudentFearSolution.student_id == student.id,
            )
        )
        rows = list(existing.scalars().all())
        if rows:
            return [
                {
                    "solution_id": r.id,
                    "fear_name": r.fear_name,
                    "solution_data": r.solution_plan,
                }
                for r in rows
            ]

        answer_map = dict(responses or {})
        if not any(
            k in answer_map
            for k in ("placement_pressure", "technical_confidence", "communication_fear")
        ):
            rows = list(
                (
                    await db.execute(
                        select(PrivateStudentResponse).where(
                            PrivateStudentResponse.checkin_id == checkin_id
                        )
                    )
                ).scalars().all()
            )
            answer_map = {}
            for row in rows:
                if isinstance(row.response_value, dict):
                    answer_map[row.question_key] = row.response_value
        initial = self.compute_initial_fear_factor(answer_map)
        fears = self.fears_from_blockers(blockers, initial_severity=initial)
        solutions = await self.generate_fear_solutions(db, checkin_id, student, fears)
        await self.schedule_6_week_notifications(db, student.id, checkin_id)
        return solutions

    async def get_current_severity(
        self,
        db: AsyncSession,
        student_id: int,
        fear_id: str,
        checkin_id: Optional[int] = None,
    ) -> tuple[int, int]:
        """
        Return (severity_before_for_next_week, initial_severity).
        Uses latest weekly progress after, else solution initial severity.
        """
        sol_q = select(PrivateStudentFearSolution).where(
            PrivateStudentFearSolution.student_id == student_id,
            PrivateStudentFearSolution.fear_id == fear_id,
        )
        if checkin_id is not None:
            sol_q = sol_q.where(PrivateStudentFearSolution.checkin_id == checkin_id)
        sol_q = sol_q.order_by(PrivateStudentFearSolution.id.desc()).limit(1)
        sol = (await db.execute(sol_q)).scalar_one_or_none()
        initial = int(sol.fear_severity) if sol else 8
        if sol is not None and sol.current_severity is not None:
            return int(sol.current_severity), initial

        prog_q = select(PrivateStudentWeeklyProgress).where(
            PrivateStudentWeeklyProgress.student_id == student_id,
            PrivateStudentWeeklyProgress.fear_id == fear_id,
        )
        if checkin_id is not None:
            prog_q = prog_q.where(
                (PrivateStudentWeeklyProgress.checkin_id == checkin_id)
                | (PrivateStudentWeeklyProgress.checkin_id.is_(None))
            )
        prog_q = prog_q.order_by(PrivateStudentWeeklyProgress.week_number.desc()).limit(1)
        latest = (await db.execute(prog_q)).scalar_one_or_none()
        if latest is not None:
            return int(latest.severity_after), initial
        return initial, initial

    def compute_severity_after(
        self,
        severity_before: int,
        self_assessment: float,
        actions_completed: int,
        actions_total: int,
    ) -> int:
        """Reduce severity based on actions + self-assessment (DB-backed chain)."""
        completion = 0.0
        if actions_total > 0:
            completion = max(0.0, min(1.0, actions_completed / float(actions_total)))
        assessment = max(0.0, min(10.0, float(self_assessment))) / 10.0
        # 0.5–2.5 points reduction per week typically
        reduction = int(round(0.5 + (completion * 1.0) + (assessment * 1.0)))
        return max(0, min(10, severity_before - reduction))

    async def submit_weekly_progress(
        self,
        db: AsyncSession,
        student_id: int,
        checkin_id: int,
        fear_id: str,
        week_number: int,
        actions_completed: int,
        actions_total: int,
        self_assessment: float,
        challenges: Optional[str] = None,
        commitment: Optional[str] = None,
    ) -> dict:
        """Full weekly progress flow with severity read from DB."""
        # Ownership: solution must belong to student/checkin
        sol = (
            await db.execute(
                select(PrivateStudentFearSolution).where(
                    PrivateStudentFearSolution.student_id == student_id,
                    PrivateStudentFearSolution.checkin_id == checkin_id,
                    PrivateStudentFearSolution.fear_id == fear_id,
                )
            )
        ).scalar_one_or_none()
        if not sol:
            raise PermissionError("Fear plan not found for this check-in.")

        severity_before, _initial = await self.get_current_severity(
            db, student_id, fear_id, checkin_id=checkin_id
        )
        # If student already logged this week, use that week's before
        existing_week_q = select(PrivateStudentWeeklyProgress).where(
            PrivateStudentWeeklyProgress.student_id == student_id,
            PrivateStudentWeeklyProgress.fear_id == fear_id,
            PrivateStudentWeeklyProgress.week_number == week_number,
        )
        if checkin_id is not None:
            existing_week_q = existing_week_q.where(
                (PrivateStudentWeeklyProgress.checkin_id == checkin_id)
                | (PrivateStudentWeeklyProgress.checkin_id.is_(None))
            )
        existing_week = (await db.execute(existing_week_q)).scalar_one_or_none()
        if existing_week:
            severity_before = int(existing_week.severity_before)

        severity_after = self.compute_severity_after(
            severity_before, self_assessment, actions_completed, actions_total
        )

        feedback = await self.generate_weekly_feedback(
            db=db,
            student_id=student_id,
            fear_id=fear_id,
            week_num=week_number,
            actions_completed=actions_completed,
            actions_total=actions_total,
            self_assessment=self_assessment,
            severity_before=severity_before,
            severity_after=severity_after,
            challenges=challenges,
        )

        if existing_week:
            existing_week.actions_completed = actions_completed
            existing_week.actions_total = actions_total
            existing_week.self_reported_improvement = self_assessment
            existing_week.ai_feedback = json.dumps(feedback)
            existing_week.severity_before = severity_before
            existing_week.severity_after = severity_after
            existing_week.challenges = challenges
            existing_week.next_week_commitment = commitment
            if checkin_id is not None:
                existing_week.checkin_id = checkin_id
            await db.flush()
            await self._check_and_create_milestones(
                db, student_id, fear_id, week_number, severity_after
            )
        else:
            await self.save_weekly_progress(
                db=db,
                student_id=student_id,
                fear_id=fear_id,
                week_num=week_number,
                actions_completed=actions_completed,
                actions_total=actions_total,
                self_assessment=self_assessment,
                severity_before=severity_before,
                severity_after=severity_after,
                ai_feedback=feedback,
                challenges=challenges,
                commitment=commitment,
                checkin_id=checkin_id,
            )

        # Honesty can lower the live score further, never raise it after tools.
        live = int(sol.current_severity) if sol.current_severity is not None else severity_before
        sol.current_severity = min(live, severity_after)
        await db.flush()

        return {
            "week": week_number,
            "fear_id": fear_id,
            "feedback": feedback,
            "severity_before": severity_before,
            "severity_after": int(sol.current_severity),
            "milestone_reached": int(sol.current_severity) == 0,
        }

    async def get_intervention_status(
        self,
        db: AsyncSession,
        student_id: int,
        checkin_id: int,
    ) -> dict:
        """Build real intervention status from solutions + weekly progress."""
        sols = list(
            (
                await db.execute(
                    select(PrivateStudentFearSolution).where(
                        PrivateStudentFearSolution.student_id == student_id,
                        PrivateStudentFearSolution.checkin_id == checkin_id,
                    )
                )
            ).scalars().all()
        )
        if not sols:
            return {
                "checkin_id": checkin_id,
                "student_id": student_id,
                "status": "awaiting_solutions",
                "week_current": 0,
                "weeks_remaining": 6,
                "fear_factor": None,
                "fear_factor_initial": None,
                "lock_days": PLAN_LOCK_DAYS,
                "fears": [],
                "overall_progress_percent": 0,
                "milestones_achieved": 0,
                "solutions": [],
            }

        fears_out = []
        max_week = 0
        total_reduction = 0
        total_initial = 0

        actions = list(
            (
                await db.execute(
                    select(PrivateStudentPlanAction).where(
                        PrivateStudentPlanAction.student_id == student_id,
                        PrivateStudentPlanAction.checkin_id == checkin_id,
                    )
                )
            ).scalars().all()
        )
        done_by_fear: dict[str, list[str]] = {}
        for act in actions:
            done_by_fear.setdefault(act.fear_id, []).append(act.tool_code)

        for sol in sols:
            latest_q = select(PrivateStudentWeeklyProgress).where(
                PrivateStudentWeeklyProgress.student_id == student_id,
                PrivateStudentWeeklyProgress.fear_id == sol.fear_id,
            )
            latest_q = latest_q.where(
                (PrivateStudentWeeklyProgress.checkin_id == checkin_id)
                | (PrivateStudentWeeklyProgress.checkin_id.is_(None))
            )
            latest = (
                await db.execute(
                    latest_q.order_by(PrivateStudentWeeklyProgress.week_number.desc()).limit(1)
                )
            ).scalar_one_or_none()

            initial = int(sol.fear_severity)
            if sol.current_severity is not None:
                current = int(sol.current_severity)
            elif latest is not None:
                current = int(latest.severity_after)
            else:
                current = initial
            week_num = int(latest.week_number) if latest else 0
            max_week = max(max_week, week_num)
            total_initial += initial
            total_reduction += max(0, initial - current)
            progress_pct = 0
            if initial > 0:
                progress_pct = int(round(100 * (initial - current) / initial))

            suggested = list_suggested_tools(sol.solution_plan, sol.fear_name)
            completed_tools = [
                t for t in (done_by_fear.get(sol.fear_id) or []) if t in suggested or is_scoreable_tool(t)
            ]

            fears_out.append(
                {
                    "fear_id": sol.fear_id,
                    "fear_name": sol.fear_name,
                    "severity_current": current,
                    "severity_initial": initial,
                    "week_number": week_num,
                    "progress_percent": max(0, min(100, progress_pct)),
                    "solution_id": sol.id,
                    "suggested_tools": suggested,
                    "completed_tools": completed_tools,
                    "actions_done": len(set(completed_tools)),
                    "actions_total": len(suggested) or 1,
                }
            )

        milestones = (
            await db.execute(
                select(PrivateStudentMilestone).where(
                    PrivateStudentMilestone.student_id == student_id,
                    PrivateStudentMilestone.fear_id.in_([s.fear_id for s in sols]),
                )
            )
        ).scalars().all()

        overall = 0
        if total_initial > 0:
            overall = int(round(100 * total_reduction / total_initial))

        all_zero = all(f["severity_current"] == 0 for f in fears_out)
        any_action = any(f["actions_done"] > 0 for f in fears_out)
        status = (
            "completed"
            if all_zero
            else ("in_progress" if max_week > 0 or any_action else "ready")
        )
        fear_factor = max((f["severity_current"] for f in fears_out), default=0)
        fear_factor_initial = max((f["severity_initial"] for f in fears_out), default=0)

        return {
            "checkin_id": checkin_id,
            "student_id": student_id,
            "status": status,
            "week_current": max_week,
            "weeks_remaining": max(0, 6 - max_week),
            "fear_factor": fear_factor,
            "fear_factor_initial": fear_factor_initial,
            "lock_days": PLAN_LOCK_DAYS,
            "fears": fears_out,
            "overall_progress_percent": max(0, min(100, overall)),
            "milestones_achieved": len(list(milestones)),
            "solutions": [
                {
                    "solution_id": s.id,
                    "fear_id": s.fear_id,
                    "fear_name": s.fear_name,
                    "fear_severity": s.fear_severity,
                    "solution_data": s.solution_plan,
                    "weekly_actions": s.weekly_actions,
                    "resources": s.resources,
                }
                for s in sols
            ],
        }

    async def complete_intervention(
        self,
        db: AsyncSession,
        student_id: int,
        checkin_id: int,
    ) -> dict:
        """Aggregate real stats and generate celebration."""
        status = await self.get_intervention_status(db, student_id, checkin_id)
        fears = status.get("fears") or []
        progress_rows = list(
            (
                await db.execute(
                    select(PrivateStudentWeeklyProgress).where(
                        PrivateStudentWeeklyProgress.student_id == student_id,
                        PrivateStudentWeeklyProgress.fear_id.in_(
                            [f["fear_id"] for f in fears] or ["__none__"]
                        ),
                    )
                )
            ).scalars().all()
        )

        actions_completed = sum(p.actions_completed for p in progress_rows)
        actions_target = sum(p.actions_total for p in progress_rows) or 1
        conquered = sum(1 for f in fears if f.get("severity_current", 1) == 0)
        initial_avg = (
            int(round(sum(f["severity_initial"] for f in fears) / len(fears)))
            if fears
            else 8
        )
        weeks_taken = status.get("week_current") or 0

        notifs = list(
            (
                await db.execute(
                    select(PrivateStudentNotification).where(
                        PrivateStudentNotification.student_id == student_id,
                        PrivateStudentNotification.checkin_id == checkin_id,
                    )
                )
            ).scalars().all()
        )
        sent = sum(1 for n in notifs if n.sent_date)
        clicked = sum(1 for n in notifs if n.clicked)
        engagement = (clicked / sent) if sent else 0.0

        stats = {
            "student_id": student_id,
            "total_fears": len(fears),
            "fears_conquered": conquered,
            "initial_fear": initial_avg,
            "actions_completed": actions_completed,
            "actions_target": actions_target,
            "weeks_taken": weeks_taken,
            "avg_improvement": round(actions_completed / max(weeks_taken, 1), 2),
            "engagement_rate": round(engagement, 2),
        }

        celebration = await self.generate_final_celebration(
            db, student_id, checkin_id, stats
        )

        # Upsert summary stats row
        existing_stats = (
            await db.execute(
                select(PrivateStudentInterventionStats).where(
                    PrivateStudentInterventionStats.student_id == student_id,
                    PrivateStudentInterventionStats.checkin_id == checkin_id,
                )
            )
        ).scalar_one_or_none()

        now = utc_now()
        payload = dict(
            total_fears=stats["total_fears"],
            fears_conquered=stats["fears_conquered"],
            total_actions_completed=actions_completed,
            total_actions_target=actions_target,
            completion_rate=round(actions_completed / actions_target, 2),
            average_improvement_per_week=float(stats["avg_improvement"]),
            total_fear_reduction=sum(
                max(0, f["severity_initial"] - f["severity_current"]) for f in fears
            ),
            notifications_sent=sent,
            notifications_clicked=clicked,
            engagement_rate=float(stats["engagement_rate"]),
            days_to_zero_fear=weeks_taken * 7 if conquered == len(fears) and fears else None,
            final_celebration=json.dumps(celebration),
            completed_at=now if conquered == len(fears) and fears else None,
        )
        if existing_stats:
            for k, v in payload.items():
                setattr(existing_stats, k, v)
        else:
            db.add(
                PrivateStudentInterventionStats(
                    student_id=student_id,
                    checkin_id=checkin_id,
                    **payload,
                )
            )
        await db.flush()

        return {
            "success": True,
            "message": "Intervention complete - you're ready for placement!"
            if conquered == len(fears) and fears
            else "Journey saved — keep going until all fears reach 0.",
            "celebration": celebration,
            "stats": stats,
            "status": status,
        }

    async def dispatch_due_notifications(self, db: AsyncSession) -> int:
        """Mark due private notifications as sent. Returns count dispatched."""
        now = utc_now()
        due = list(
            (
                await db.execute(
                    select(PrivateStudentNotification).where(
                        PrivateStudentNotification.sent_date.is_(None),
                        PrivateStudentNotification.scheduled_date <= now,
                    ).limit(200)
                )
            ).scalars().all()
        )
        for n in due:
            n.sent_date = now
        if due:
            await db.flush()
            logger.info("Dispatched %s Fear → Fearless notifications", len(due))
        return len(due)

    async def list_notifications(
        self,
        db: AsyncSession,
        student_id: int,
        *,
        unread_only: bool = False,
    ) -> list[dict]:
        """List notifications for student (private inbox)."""
        q = select(PrivateStudentNotification).where(
            PrivateStudentNotification.student_id == student_id,
            PrivateStudentNotification.sent_date.is_not(None),
        )
        if unread_only:
            q = q.where(PrivateStudentNotification.clicked.is_(False))
        q = q.order_by(PrivateStudentNotification.scheduled_date.desc()).limit(50)
        rows = list((await db.execute(q)).scalars().all())
        return [
            {
                "id": n.id,
                "checkin_id": n.checkin_id,
                "notification_type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "cta_text": n.cta_text,
                "scheduled_date": n.scheduled_date.isoformat() if n.scheduled_date else None,
                "sent_date": n.sent_date.isoformat() if n.sent_date else None,
                "clicked": bool(n.clicked),
            }
            for n in rows
        ]

    async def mark_notification_clicked(
        self,
        db: AsyncSession,
        student_id: int,
        notification_id: int,
    ) -> dict:
        n = await db.get(PrivateStudentNotification, notification_id)
        if not n or n.student_id != student_id:
            raise PermissionError("Notification not found.")
        n.clicked = True
        n.clicked_at = utc_now()
        await db.flush()
        return {"id": n.id, "clicked": True}

    async def apply_tool_completion(
        self,
        db: AsyncSession,
        student_id: int,
        checkin_id: int,
        fear_id: str,
        tool_code: str,
        *,
        action_key: Optional[str] = None,
        source: str = "tool",
    ) -> dict:
        """Record a suggested mock/test and lower the fear factor toward 0."""
        sol = (
            await db.execute(
                select(PrivateStudentFearSolution).where(
                    PrivateStudentFearSolution.student_id == student_id,
                    PrivateStudentFearSolution.checkin_id == checkin_id,
                    PrivateStudentFearSolution.fear_id == fear_id,
                )
            )
        ).scalar_one_or_none()
        if not sol:
            # If the client omitted fear_id, apply to the heaviest remaining fear
            # that lists this tool — or the first fear on the check-in.
            sols = list(
                (
                    await db.execute(
                        select(PrivateStudentFearSolution).where(
                            PrivateStudentFearSolution.student_id == student_id,
                            PrivateStudentFearSolution.checkin_id == checkin_id,
                        )
                    )
                ).scalars().all()
            )
            if not sols:
                raise PermissionError("Fear plan not found for this check-in.")
            code = normalize_tool_code(tool_code)
            match = None
            for row in sols:
                suggested = list_suggested_tools(row.solution_plan, row.fear_name)
                if code in suggested:
                    match = row
                    break
            sol = match or max(
                sols,
                key=lambda r: int(
                    r.current_severity if r.current_severity is not None else r.fear_severity
                ),
            )
            fear_id = sol.fear_id

        code = normalize_tool_code(tool_code)
        if not code:
            raise ValueError("Missing tool code.")
        if not is_scoreable_tool(code):
            # Still record soft actions (mentor / practice / home) but they
            # only count if they appear on the suggested list.
            pass

        suggested = list_suggested_tools(sol.solution_plan, sol.fear_name)
        counts_for_score = code in suggested or is_scoreable_tool(code)

        existing = (
            await db.execute(
                select(PrivateStudentPlanAction).where(
                    PrivateStudentPlanAction.checkin_id == checkin_id,
                    PrivateStudentPlanAction.fear_id == sol.fear_id,
                    PrivateStudentPlanAction.tool_code == code,
                )
            )
        ).scalar_one_or_none()

        already = existing is not None
        if not existing:
            db.add(
                PrivateStudentPlanAction(
                    checkin_id=checkin_id,
                    student_id=student_id,
                    fear_id=sol.fear_id,
                    tool_code=code,
                    action_key=(action_key or "")[:64] or None,
                    source=(source or "tool")[:32],
                    completed_at=utc_now(),
                )
            )
            await db.flush()

        done_rows = list(
            (
                await db.execute(
                    select(PrivateStudentPlanAction).where(
                        PrivateStudentPlanAction.checkin_id == checkin_id,
                        PrivateStudentPlanAction.fear_id == sol.fear_id,
                    )
                )
            ).scalars().all()
        )
        done_codes = {r.tool_code for r in done_rows}
        done_for_score = [t for t in suggested if t in done_codes]
        if not suggested:
            done_for_score = [t for t in done_codes if is_scoreable_tool(t)]
            suggested = list(SCOREABLE_TOOLS)[:4]

        initial = int(sol.fear_severity)
        before = (
            int(sol.current_severity)
            if sol.current_severity is not None
            else initial
        )
        after = severity_from_tool_progress(initial, len(done_for_score), len(suggested))
        if counts_for_score:
            sol.current_severity = after
        else:
            after = before
        await db.flush()

        if after == 0 and before > 0:
            days = max(1, (utc_now() - (sol.created_at or utc_now())).days)
            week_num = min(6, max(1, (days // 7) + 1))
            await self._check_and_create_milestones(
                db, student_id, sol.fear_id, week_num, after
            )

        status = await self.get_intervention_status(db, student_id, checkin_id)
        return {
            "already_recorded": already,
            "fear_id": sol.fear_id,
            "tool_code": code,
            "severity_before": before,
            "severity_after": after,
            "fear_factor": status.get("fear_factor"),
            "fear_factor_initial": status.get("fear_factor_initial"),
            "actions_done": len(done_for_score),
            "actions_total": len(suggested) or 1,
            "suggested_tools": suggested,
            "completed_tools": sorted(done_codes),
            "intervention": status,
        }


def default_suggested_tools(fear_name: str) -> list[str]:
    """Scoreable mocks that match this fear when the stored plan has none."""
    key = str(fear_name or "").lower()
    if any(w in key for w in ("aptitude", "quant", "lr", "reasoning")):
        return ["aptitude", "skill_readiness"]
    if any(w in key for w in ("english", "speak", "hr", "introduc", "communicat")):
        return ["hr_mock", "interview_mock"]
    if any(w in key for w in ("project", "explain")):
        return ["project_mock", "interview_mock"]
    if any(w in key for w in ("cod", "dsa", "leetcode", "solution", "copy")):
        return ["coding", "skill_mock"]
    if any(w in key for w in ("skill", "technical", "foundation")):
        return ["skill_readiness", "skill_mock", "interview_mock"]
    return ["skill_readiness", "aptitude", "interview_mock", "hr_mock"]


def list_suggested_tools(solution_plan: Optional[dict], fear_name: str = "") -> list[str]:
    """Unique scoreable tools mentioned in the 6-week plan."""
    found: list[str] = []
    seen: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ("tool", "tool_code", "widget") and isinstance(val, str):
                    code = normalize_tool_code(val)
                    if is_scoreable_tool(code) and code not in seen:
                        seen.add(code)
                        found.append(code)
                else:
                    _walk(val)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(solution_plan or {})
    if not found:
        return default_suggested_tools(fear_name)
    return found


def severity_from_tool_progress(initial: int, done: int, total: int) -> int:
    """Drop the 0–10 score in even steps; all suggested tools done → 0."""
    start = max(0, min(10, int(initial)))
    if total <= 0:
        return start
    done = max(0, min(int(done), int(total)))
    return max(0, int(round(start * (1 - (done / float(total))))))


def extract_weekly_actions(solution_data: dict) -> list:
    """Extract weekly action summaries from solution."""
    
    actions = []
    for week in range(1, 7):
        week_key = f"week{week}"
        if week_key in solution_data:
            week_data = solution_data[week_key]
            # Count days with actions
            daily_actions = [
                f"day{i}"
                for i in range(1, 8)
                if f"day{i}" in week_data
            ]
            actions.append(f"Week {week}: {len(daily_actions)} daily actions")
    
    return actions
