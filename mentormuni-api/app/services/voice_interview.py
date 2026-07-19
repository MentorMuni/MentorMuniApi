"""OpenAI Realtime voice interview: session minting + post-interview analysis.

1) create_session → ephemeral client secret for browser WebRTC (Realtime speech-to-speech)
2) analyze_interview → structured scoring via chat completions (GPT analysis model)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, List

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.ai import (
    VoiceInterviewAnalyzeRequest,
    VoiceInterviewAnalyzeResponse,
    VoiceInterviewSessionRequest,
    VoiceInterviewSessionResponse,
    VoiceInterviewTranscriptTurn,
)
from app.services.voice_interview_analysis_prompt import render_voice_interview_analysis_prompt
from app.services.voice_interview_prompt import render_voice_interview_prompt

logger = logging.getLogger(__name__)

OPENAI_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
MAX_TOKENS_ANALYSIS = 1200
# OpenAI has no Indian-accent male voice ID. echo/ash/verse are the clearer male personas.
_MALE_VOICES = frozenset({"echo", "ash", "verse"})
_DEFAULT_MALE_VOICE = "echo"


class VoiceInterviewService:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def create_session(
        self, body: VoiceInterviewSessionRequest
    ) -> VoiceInterviewSessionResponse:
        instructions = render_voice_interview_prompt(
            body.interview_focus,
            target_role=body.target_role,
            target_companies=body.target_companies,
            extra_context=body.extra_context,
        )
        model = body.model or settings.realtime_model
        # Force a male voice even if the client sends marin/cedar/etc.
        requested = (body.voice or _DEFAULT_MALE_VOICE).strip().lower()
        voice = requested if requested in _MALE_VOICES else _DEFAULT_MALE_VOICE
        if requested != voice:
            logger.info("Voice interview remapped voice=%s -> %s (male)", requested, voice)

        # Interviewer pacing: wait through thinking pauses; reduce noise false-triggers.
        # server_vad + longer silence = candidate can pause without bot filler.
        # Frontend must include session.type="realtime" on any session.update (GA Realtime).
        payload: dict[str, Any] = {
            "expires_after": {
                "anchor": "created_at",
                "seconds": settings.realtime_client_secret_ttl_seconds,
            },
            "session": {
                "type": "realtime",
                "model": model,
                "instructions": instructions,
                "audio": {
                    "input": {
                        "noise_reduction": {
                            "type": "far_field",
                        },
                        "transcription": {
                            "model": "gpt-4o-mini-transcribe",
                            "language": "en",
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.72,
                            "prefix_padding_ms": 250,
                            "silence_duration_ms": 1400,
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "voice": voice,
                        "speed": 0.95,
                    },
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        # Privacy-preserving identifier (hash of focus + role); never send raw PII.
        safety_seed = f"{body.interview_focus}|{body.target_role or ''}"
        headers["OpenAI-Safety-Identifier"] = hashlib.sha256(
            safety_seed.encode("utf-8")
        ).hexdigest()[:64]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                OPENAI_CLIENT_SECRETS_URL,
                headers=headers,
                json=payload,
            )

        if resp.status_code >= 400:
            detail = _safe_openai_error(resp)
            logger.error(
                "OpenAI realtime client_secrets failed status=%s detail=%s",
                resp.status_code,
                detail,
            )
            raise RuntimeError(detail)

        data = resp.json()
        client_secret = data.get("value")
        expires_at = data.get("expires_at")
        if not client_secret or expires_at is None:
            logger.error("Unexpected client_secrets response keys=%s", list(data.keys()))
            raise RuntimeError("OpenAI did not return a valid ephemeral client secret")

        preview = instructions.strip().replace("\n", " ")
        if len(preview) > 280:
            preview = preview[:277] + "..."

        return VoiceInterviewSessionResponse(
            client_secret=client_secret,
            expires_at=int(expires_at),
            model=model,
            voice=voice,
            interview_focus=body.interview_focus,
            instructions_preview=preview,
            realtime_calls_url=OPENAI_REALTIME_CALLS_URL,
            session_type="realtime",
            integration_hint=(
                "Connect WebRTC to realtime_calls_url with Bearer client_secret. "
                "Do NOT proxy audio through MentorMuni. "
                "If you send session.update on the data channel, the payload MUST include "
                "session.type = 'realtime' (OpenAI GA). Missing it causes: "
                "Missing required parameter: 'session.type'."
            ),
        )

    async def analyze_interview(
        self, body: VoiceInterviewAnalyzeRequest
    ) -> VoiceInterviewAnalyzeResponse:
        transcript_text = _format_transcript(body.transcript)
        prompt = render_voice_interview_analysis_prompt(
            body.interview_focus,
            transcript_text,
            target_role=body.target_role,
            target_companies=body.target_companies,
        )

        response = await self._client.chat.completions.create(
            model=settings.voice_interview_analysis_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You evaluate practice interviews and return ONLY valid JSON "
                        "matching the requested schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=MAX_TOKENS_ANALYSIS,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = (response.choices[0].message.content or "").strip()
        parsed = _parse_analysis_json(content)
        return VoiceInterviewAnalyzeResponse(
            technical_score=parsed["technical_score"],
            communication_score=parsed["communication_score"],
            strengths=parsed["strengths"],
            weaknesses=parsed["weaknesses"],
            study_plan=parsed["study_plan"],
            interview_focus=body.interview_focus,
            overall_score=round(
                (parsed["technical_score"] + parsed["communication_score"]) / 2
            ),
        )


def _format_transcript(turns: List[VoiceInterviewTranscriptTurn]) -> str:
    lines: List[str] = []
    for turn in turns:
        speaker = "Candidate" if turn.role == "user" else "Interviewer"
        lines.append(f"{speaker}: {turn.text}")
    return "\n".join(lines)


def _clamp_score(value: Any) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 0
    return max(0, min(100, n))


def _as_string_list(value: Any, *, min_items: int = 1, max_items: int = 6) -> List[str]:
    if not isinstance(value, list):
        return ["Not enough evidence captured in this session."]
    out: List[str] = []
    for item in value:
        s = str(item).strip()
        if s:
            out.append(s[:200])
        if len(out) >= max_items:
            break
    if len(out) < min_items:
        out.append("Not enough evidence captured in this session.")
    return out


def _parse_analysis_json(content: str) -> dict:
    raw = content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Voice interview analysis JSON parse failed: %s", e)
        raise RuntimeError("Analysis model returned invalid JSON") from e

    if not isinstance(data, dict):
        raise RuntimeError("Analysis model returned invalid JSON object")

    return {
        "technical_score": _clamp_score(data.get("technical_score")),
        "communication_score": _clamp_score(data.get("communication_score")),
        "strengths": _as_string_list(data.get("strengths"), min_items=2, max_items=5),
        "weaknesses": _as_string_list(data.get("weaknesses"), min_items=2, max_items=5),
        "study_plan": _as_string_list(data.get("study_plan"), min_items=3, max_items=6),
    }


def _safe_openai_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return f"OpenAI Realtime error: {err['message']}"
        return f"OpenAI Realtime error (HTTP {resp.status_code})"
    except Exception:
        return f"OpenAI Realtime error (HTTP {resp.status_code})"
