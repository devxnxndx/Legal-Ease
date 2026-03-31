"""
routers/voice.py  —  LegalEase AI
TTS via ElevenLabs REST API (free-tier compatible)

Endpoints
---------
GET  /api/voice/voices   → hardcoded list from the account's actual premade voices
POST /api/voice/speak    → synthesise text → audio/mpeg stream
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL_ID: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

# ---------------------------------------------------------------------------
# Verified premade voices from this account (category=premade, free tier)
# IDs sourced directly from /v1/voices response — these are confirmed valid.
# ---------------------------------------------------------------------------
FREE_VOICES = [
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah — Mature, Reassuring · American Female"},
    {"id": "CwhRBWXzGAHq8TQ4Fs17", "name": "Roger — Laid-Back, Casual · American Male"},
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George — Warm Storyteller · British Male"},
    {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel — Steady Broadcaster · British Male"},
    {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice — Clear Educator · British Female"},
    {"id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily — Velvety Actress · British Female"},
    {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda — Professional · American Female"},
    {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica — Playful, Bright · American Female"},
    {"id": "hpp4J3VqNfWAUOO0d1Us", "name": "Bella — Professional, Warm · American Female"},
    {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric — Smooth, Trustworthy · American Male"},
    {"id": "iP95p4xoKVk53GoZ742B", "name": "Chris — Charming, Down-to-Earth · American Male"},
    {"id": "nPczCjzI2devNBz1zQrb", "name": "Brian — Deep, Resonant · American Male"},
    {"id": "bIHbv24MWmeRgasZH58o", "name": "Will — Relaxed Optimist · American Male"},
    {"id": "pqHfZKP75CvOlQylNhV4", "name": "Bill — Wise, Mature · American Male"},
    {"id": "SAz9YHcvj6GT2YYXdXww", "name": "River — Relaxed, Neutral · American Neutral"},
    {"id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam — Energetic · American Male"},
    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie — Confident, Energetic · Australian Male"},
    {"id": "FGY2WhTYpPnrIDTdsKH5", "name": "Laura — Enthusiast, Quirky · American Female"},
    {"id": "N2lVS1w4EtoT3dr4eOWO", "name": "Callum — Husky Trickster · American Male"},
    {"id": "SOYHLrjzK2X1ezoPC6cr", "name": "Harry — Fierce Warrior · American Male"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam — Dominant, Firm · American Male"},
]

# Default: Sarah (first in list — professional, clear, good for legal content)
DEFAULT_VOICE_ID: str = os.getenv(
    "ELEVENLABS_DEFAULT_VOICE_ID", FREE_VOICES[0]["id"]
)

VALID_IDS = {v["id"] for v in FREE_VOICES}


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------
class SpeakRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    model_id: Optional[str] = None
    language: Optional[str] = None   # kept for API compat — ignored
    stability: Optional[float] = None
    similarity_boost: Optional[float] = None
    style: Optional[float] = None
    use_speaker_boost: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _el_headers() -> dict[str, str]:
    if not ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ELEVENLABS_API_KEY is not set. Add it to your .env file.",
        )
    return {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# GET /api/voice/voices  — no API call needed
# ---------------------------------------------------------------------------
@router.get("/voices")
async def list_voices():
    """Return the premade ElevenLabs voices available on this account."""
    return {"voices": FREE_VOICES}


# ---------------------------------------------------------------------------
# POST /api/voice/speak
# ---------------------------------------------------------------------------
@router.post("/speak")
async def speak(req: SpeakRequest):
    """Synthesise text with ElevenLabs and stream back audio/mpeg."""

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    voice_id = req.voice_id if req.voice_id in VALID_IDS else DEFAULT_VOICE_ID
    model_id = req.model_id or DEFAULT_MODEL_ID

    vs: dict = {}
    if req.stability is not None:
        vs["stability"] = max(0.0, min(1.0, req.stability))
    if req.similarity_boost is not None:
        vs["similarity_boost"] = max(0.0, min(1.0, req.similarity_boost))
    if req.style is not None:
        vs["style"] = max(0.0, min(1.0, req.style))
    if req.use_speaker_boost is not None:
        vs["use_speaker_boost"] = req.use_speaker_boost

    payload: dict = {"text": req.text, "model_id": model_id}
    if vs:
        payload["voice_settings"] = vs

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}/stream"

    try:
        timeout = httpx.Timeout(connect=10, read=120, write=30, pool=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", url, headers=_el_headers(), json=payload
            ) as el_resp:
                if el_resp.status_code != 200:
                    body = await el_resp.aread()
                    logger.error(
                        "ElevenLabs TTS error %s: %s",
                        el_resp.status_code,
                        body.decode(errors="replace"),
                    )
                    raise HTTPException(
                        status_code=el_resp.status_code,
                        detail=body.decode(errors="replace"),
                    )
                audio_bytes = await el_resp.aread()

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={
                "X-Spoken-Summary": req.text[:200].replace("\n", " "),
                "Content-Length": str(len(audio_bytes)),
                "Cache-Control": "no-store",
            },
        )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ElevenLabs TTS request timed out.")
    except Exception as exc:
        logger.exception("Unexpected error during TTS synthesis")
        raise HTTPException(status_code=500, detail=str(exc))