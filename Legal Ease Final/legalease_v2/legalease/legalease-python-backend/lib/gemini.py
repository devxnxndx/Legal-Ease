"""
Gemini helpers used by the LegalEase AI backend.

Models used:
  • gemini-2.5-flash             — chat + STT transcription + speech summarisation
  • models/gemini-embedding-001  — text embeddings (768-dim)
  • gemini-2.5-flash-preview-tts — text-to-speech (REST endpoint)

All blocking SDK calls are wrapped in run_in_executor so they don't block
the FastAPI event loop.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json as _json
import os
import re
import struct
from typing import AsyncGenerator

import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)


def _configure_genai():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing in environment variables")
    genai.configure(api_key=api_key)


# ---------------------------------------------------------------------------
# System instruction for the legal chat model
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are LegalEase AI.

You analyze and explain legal documents.
You do NOT provide legal advice.

Rules:
- Answer only using the provided document context
- Do not invent facts
- Do not recommend actions (e.g., "you should", "you must", "you can sue")
- Do not give legal conclusions or judgments
- Explain what the document says, not what the user should do
- Use plain, neutral language
- Cite page numbers when possible
- If context is insufficient, say so clearly

If a user asks for advice, respond by clarifying:
"I can explain what the document says, but I cannot provide legal advice."\
"""


# ---------------------------------------------------------------------------
# Helper: run a sync callable in the default thread pool
# ---------------------------------------------------------------------------
async def _run(fn):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn)


def _is_rate_limit_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "429" in msg
        or "quota" in msg
        or "resource_exhausted" in msg
        or "rate limit" in msg
        or "too many requests" in msg
    )


async def _run_with_retry(fn, max_retries: int = 3, base_delay: int = 5):
    """
    Retry helper for non-interactive/background-style calls where a small retry
    is acceptable (used mainly for embeddings).
    """
    for attempt in range(max_retries):
        try:
            return await _run(fn)
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)  # 5s, 10s, 20s
                print(f"[gemini] Rate limited (attempt {attempt + 1}). Retrying in {wait}s...")
                await asyncio.sleep(wait)
                continue
            raise
    raise RuntimeError("Max retries exceeded due to Gemini rate limiting.")


async def _run_fast_fail(fn):
    """
    Fail fast for interactive/user-facing Gemini calls.
    Do NOT sit in long retry loops for chat or analysis generation.
    """
    try:
        return await _run(fn)
    except Exception as e:
        if _is_rate_limit_error(e):
            raise RuntimeError(
                "Gemini quota exceeded or rate limited. Please try again later."
            ) from e
        raise


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
async def embed_text(text: str) -> list[float]:
    """Return a 768-dim embedding vector for a single text string."""
    _configure_genai()
    result = await _run(
        lambda: genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            output_dimensionality=768,
        )
    )
    return result["embedding"]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    _configure_genai()
    if not texts:
        return []

    # genai.embed_content accepts a list of strings and returns multiple embeddings in one API call
    result = await _run_with_retry(
        lambda: genai.embed_content(
            model="models/gemini-embedding-001",
            content=texts,
            output_dimensionality=768,
        )
    )
    
    return result["embedding"]


# ---------------------------------------------------------------------------
# Chat with streaming
# ---------------------------------------------------------------------------
async def stream_chat_with_context(
    message: str,
    rag_context: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Yield text tokens one-by-one from Gemini, given RAG context and
    a conversation history list of {"role": "user"|"ai", "content": str}.
    """
    _configure_genai()
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=_SYSTEM_INSTRUCTION,
    )

    if rag_context:
        contextual_prompt = (
            f"RELEVANT DOCUMENT EXCERPTS:\n{rag_context}\n\n---\nUser question: {message}"
        )
    else:
        contextual_prompt = message

    chat_history = [
        {
            "role": "model" if h.get("role") == "ai" else "user",
            "parts": [h.get("content", "")],
        }
        for h in history
    ]

    def _send():
        print(chat_history)
        chat = model.start_chat(history=chat_history)
        res = chat.send_message(
            contextual_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=512,
            ),
            stream=True,
        
        )
        print(res)
        return(res)
    response = await _run_fast_fail(_send)

    for chunk in response:
        if getattr(chunk, "text", None):
            yield chunk.text


# ---------------------------------------------------------------------------
# Speech-to-text (transcription)
# ---------------------------------------------------------------------------
def _clean_audio_mime_type(mime_type: str | None) -> str:
    if not mime_type:
        return "audio/wav"

    clean = mime_type.split(";", 1)[0].strip().lower()

    alias_map = {
        "audio/x-wav": "audio/wav",
        "audio/mp3": "audio/mpeg",
        "audio/x-aiff": "audio/aiff",
    }

    return alias_map.get(clean, clean)


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Transcribe an audio recording using Gemini's multimodal capabilities.
    Preserves the original language — Hindi stays Hindi, Tamil stays Tamil, etc.
    Returns the raw transcript string.
    """
    if not audio_bytes:
        raise RuntimeError("transcribe_audio received empty audio bytes.")

    _configure_genai()
    model = genai.GenerativeModel("gemini-2.5-flash")

    normalized_mime_type = _clean_audio_mime_type(mime_type)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    result = await _run_fast_fail(
        lambda: model.generate_content(
            [
                {"mime_type": normalized_mime_type, "data": audio_b64},
                (
                    "Transcribe the speech in this audio recording exactly as spoken. "
                    "Do NOT translate it. If the person speaks Hindi, output Hindi text "
                    "in Devanagari script. If Tamil, output Tamil script, and so on for "
                    "any other Indian or international language. "
                    "Return only the transcribed text — no labels, no commentary."
                ),
            ]
        )
    )

    transcript = (getattr(result, "text", "") or "").strip()
    if not transcript:
        raise RuntimeError("Gemini transcription returned empty text.")
    return transcript


# ---------------------------------------------------------------------------
# Text-to-speech helpers
# ---------------------------------------------------------------------------
LANGUAGE_LABELS = {
    "auto": "Auto-detect",
    "english": "English",
    "hindi": "Hindi",
    "bengali": "Bengali",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "marathi": "Marathi",
    "kannada": "Kannada",
    "malayalam": "Malayalam",
    "gujarati": "Gujarati",
    "punjabi": "Punjabi",
    "urdu": "Urdu",
    "french": "French",
    "german": "German",
    "spanish": "Spanish",
    "arabic": "Arabic",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "korean": "Korean",
    "italian": "Italian",
    "portuguese": "Portuguese",
    "russian": "Russian",
}

_LANG_TO_GTTS: dict[str, str] = {
    "english": "en",
    "hindi": "hi",
    "bengali": "bn",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "kannada": "kn",
    "malayalam": "ml",
    "gujarati": "gu",
    "punjabi": "pa",
    "urdu": "ur",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "arabic": "ar",
    "chinese": "zh-CN",
    "japanese": "ja",
    "korean": "ko",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    # extra tolerated aliases
    "odia": "or",
    "assamese": "as",
    "nepali": "ne",
    "sinhala": "si",
}


def _normalize_language_key(language: str | None) -> str:
    if not language:
        return "english"

    key = language.strip().lower()

    alias_map = {
        "en": "english",
        "hi": "hindi",
        "bn": "bengali",
        "ta": "tamil",
        "te": "telugu",
        "mr": "marathi",
        "kn": "kannada",
        "ml": "malayalam",
        "gu": "gujarati",
        "pa": "punjabi",
        "ur": "urdu",
        "fr": "french",
        "de": "german",
        "es": "spanish",
        "ar": "arabic",
        "zh": "chinese",
        "zh-cn": "chinese",
        "ja": "japanese",
        "ko": "korean",
        "it": "italian",
        "pt": "portuguese",
        "ru": "russian",
    }

    return alias_map.get(key, key)


async def summarize_for_speech(full_text: str, language: str = "auto") -> str:
    """
    Condense a (potentially long) AI response into 2-4 sentences suitable
    for being read aloud.

    When language="auto", Gemini auto-detects the language of the text and
    produces the summary in that same language. It prepends a machine-readable
    tag like [LANG:hindi] so downstream TTS knows which language code to use.
    """
    _configure_genai()
    model = genai.GenerativeModel("gemini-2.5-flash")

    target_language = _normalize_language_key(language)

    if target_language == "auto":
        lang_instruction = (
            "First, detect the primary language of the text below.\n"
            "Then produce your spoken summary in THAT SAME language.\n"
            "Prepend a single tag on its own line: [LANG:<language_name_lowercase>]\n"
            "For example: [LANG:hindi] or [LANG:english] or [LANG:tamil]\n"
        )
    else:
        label = LANGUAGE_LABELS.get(target_language, target_language.title())
        lang_instruction = (
            f"Produce the spoken summary in {label}.\n"
            f"Prepend a single tag on its own line: [LANG:{target_language}]\n"
        )

    prompt = (
        "You are summarising a legal AI response to be read aloud.\n"
        f"{lang_instruction}"
        "Then write a concise spoken summary — 2 to 4 sentences maximum.\n"
        "Be precise and natural-sounding. Drop page citations, source tags, and markdown.\n"
        "Only return the tag line and the summary text, nothing else.\n\n"
        f"Response to summarise:\n{full_text}"
    )

    result = await _run_fast_fail(
        lambda: model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
    )

    summary = (getattr(result, "text", "") or "").strip()
    if not summary:
        raise RuntimeError("Gemini speech summary returned empty text.")
    return summary


def _parse_lang_tag(text: str) -> tuple[str, str]:
    """
    Parse a [LANG:xyz] tag from the first non-empty line of text.
    Returns (language_name, clean_text_without_tag).
    """
    stripped = (text or "").strip()
    match = re.match(r"^\[LANG:([a-zA-Z0-9\-]+)\]\s*", stripped)
    if match:
        lang = _normalize_language_key(match.group(1))
        clean = stripped[match.end():].strip()
        return lang, clean

    return "english", stripped


def _resolve_tts_language(text: str, language: str) -> tuple[str, str, str]:
    detected_lang, clean_text = _parse_lang_tag(text)

    explicit_lang = _normalize_language_key(language)
    if explicit_lang != "auto":
        target_lang = explicit_lang
    else:
        target_lang = detected_lang

    lang_code = _LANG_TO_GTTS.get(target_lang, "en")
    return target_lang, lang_code, clean_text


async def synthesize_speech(text: str, language: str = "auto") -> bytes:
    """
    Generate speech audio from text.
    Uses gTTS first and falls back to Gemini TTS if needed.

    Returns MP3 bytes (gTTS path) or WAV bytes (Gemini fallback).
    """
    from gtts import gTTS as GoogleTTS

    target_lang, lang_code, clean_text = _resolve_tts_language(text, language)

    if not clean_text:
        raise RuntimeError("No text available for speech synthesis.")

    print(
        f"[tts] Synthesising speech — target_lang={target_lang}, "
        f"gTTS code={lang_code}, text length={len(clean_text)}"
    )

    try:
        def _generate_gtts() -> bytes:
            tts = GoogleTTS(text=clean_text, lang=lang_code, slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()

        mp3_bytes = await _run(_generate_gtts)
        if not mp3_bytes:
            raise RuntimeError("gTTS returned empty audio.")
        return mp3_bytes

    except Exception as e:
        print(f"[tts] gTTS failed ({e}), falling back to Gemini TTS…")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing in environment variables")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    )

    language_prefix = (
        f"Please speak the following text in {target_lang}.\n\n"
        if target_lang != "english"
        else ""
    )

    body = {
        "contents": [{"parts": [{"text": language_prefix + clean_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Aoede"}
                }
            },
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(url, json=body)
        if res.status_code != 200:
            raise RuntimeError(f"Gemini TTS failed ({res.status_code}): {res.text}")
        data = res.json()

    try:
        audio_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except Exception as exc:
        raise RuntimeError(f"Unexpected Gemini TTS response shape: {data}") from exc

    pcm_bytes = base64.b64decode(audio_b64)
    if not pcm_bytes:
        raise RuntimeError("Gemini TTS returned empty audio payload.")

    return _build_wav(
        pcm_bytes,
        sample_rate=24000,
        num_channels=1,
        bits_per_sample=16,
    )


def _build_wav(
    pcm: bytes,
    sample_rate: int,
    num_channels: int,
    bits_per_sample: int,
) -> bytes:
    """Wrap raw PCM bytes in a minimal WAV header."""
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm


# ---------------------------------------------------------------------------
# Auto-summary generation
# ---------------------------------------------------------------------------
async def generate_summary(chunks_text: str) -> str:
    """
    Generate a 3-5 sentence summary of a legal document from its chunk text.
    Used automatically after upload processing completes.
    """
    _configure_genai()
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = (
        "You are an expert legal document analyst.\n"
        "Summarise the following legal document in 3 to 5 clear, concise sentences.\n"
        "Focus on: parties involved, subject matter, key obligations, important dates, "
        "and any notable terms or conditions.\n"
        "Use plain language. Do not use markdown formatting.\n"
        "Only return the summary text, nothing else.\n\n"
        f"DOCUMENT TEXT:\n{chunks_text[:8000]}"
    )

    result = await _run_fast_fail(
        lambda: model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
    )
    return (getattr(result, "text", "") or "").strip()


# ---------------------------------------------------------------------------
# Contract risk scoring
# ---------------------------------------------------------------------------
async def score_contract_risk(chunks_text: str) -> dict:
    """
    Analyse a legal document and return a risk score (1-10) with explanation.

    Returns:
        {"score": int, "explanation": str, "factors": [str, ...]}
    """
    _configure_genai()
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = (
        "You are a senior legal risk analyst.\n"
        "Analyse the following legal document and rate its risk level from 1 (very low risk) "
        "to 10 (extremely high risk).\n\n"
        "Consider these risk factors:\n"
        "- Unlimited or broad indemnity clauses\n"
        "- Missing liability caps\n"
        "- One-sided termination rights\n"
        "- Aggressive penalty or liquidated damages clauses\n"
        "- Broad IP assignment or non-compete clauses\n"
        "- Missing dispute resolution mechanisms\n"
        "- Auto-renewal traps\n"
        "- Ambiguous or vague language\n\n"
        "Respond ONLY with valid JSON in this exact format (no markdown, no code fences):\n"
        '{"score": <integer 1-10>, "explanation": "<2-3 sentence explanation>", '
        '"factors": ["<risk factor 1>", "<risk factor 2>", ...]}\n\n'
        f"DOCUMENT TEXT:\n{chunks_text[:8000]}"
    )

    result = await _run_fast_fail(
        lambda: model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
    )

    text = (getattr(result, "text", "") or "").strip()

    try:
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        if not text or "Internal Server Error" in text:
            raise ValueError("Invalid Gemini response")

        return _json.loads(text)

    except Exception:
        print("[gemini] JSON parse failed in score_contract_risk:", text[:200] if text else "EMPTY")
        return {"score": 5, "explanation": "Could not fully analyse risk.", "factors": []}


# ---------------------------------------------------------------------------
# Clause auto-tagger
# ---------------------------------------------------------------------------
async def detect_clauses(chunks_text: str) -> list[dict]:
    """
    Detect standard clause types in a legal document.

    Returns:
        [{"type": str, "excerpt": str, "page": int}, ...]

    Clause types: indemnity, limitation_of_liability, termination,
    confidentiality, payment, non_compete, ip_assignment, dispute_resolution,
    force_majeure, warranty, governing_law, data_protection
    """
    _configure_genai()
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = (
        "You are a legal document clause classifier.\n"
        "Identify all standard clause types present in the following document.\n\n"
        "Recognised clause types:\n"
        "indemnity, limitation_of_liability, termination, confidentiality, payment, "
        "non_compete, ip_assignment, dispute_resolution, force_majeure, warranty, "
        "governing_law, data_protection\n\n"
        "For each clause found, provide:\n"
        "- type: one of the clause types above\n"
        "- excerpt: a key sentence (max 120 chars) from the clause\n"
        "- page: estimated page number (1-indexed)\n\n"
        "Respond ONLY with a valid JSON array (no markdown, no code fences):\n"
        '[{"type": "...", "excerpt": "...", "page": 1}, ...]\n\n'
        "If no clauses are found, return an empty array: []\n\n"
        f"DOCUMENT TEXT:\n{chunks_text[:10000]}"
    )

    result = await _run_fast_fail(
        lambda: model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
    )

    text = (getattr(result, "text", "") or "").strip()

    try:
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        if not text or "Internal Server Error" in text:
            raise ValueError("Invalid Gemini response")

        return _json.loads(text)

    except Exception:
        print("[gemini] JSON parse failed in detect_clauses:", text[:200] if text else "EMPTY")
        return []


# ---------------------------------------------------------------------------
# Deadline extractor
# ---------------------------------------------------------------------------
async def extract_deadlines(chunks_text: str) -> list[dict]:
    """
    Extract all dates and deadlines from a legal document.

    Returns:
        [{"date": str, "event": str, "description": str, "page": int}, ...]
    """
    _configure_genai()
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = (
        "You are a legal document deadline analyst.\n"
        "Extract ALL dates, deadlines, and time-sensitive obligations from the document.\n\n"
        "For each deadline found, provide:\n"
        "- date: the date or timeframe (e.g. '2024-06-30', '30 days after signing', "
        "'within 14 business days')\n"
        "- event: short label (e.g. 'Payment Due', 'Contract Expiry', 'Notice Period')\n"
        "- description: one sentence describing the obligation\n"
        "- page: estimated page number (1-indexed)\n\n"
        "Respond ONLY with a valid JSON array (no markdown, no code fences):\n"
        '[{"date": "...", "event": "...", "description": "...", "page": 1}, ...]\n\n'
        "If no deadlines are found, return an empty array: []\n\n"
        f"DOCUMENT TEXT:\n{chunks_text[:10000]}"
    )

    result = await _run_fast_fail(
        lambda: model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
    )

    text = (getattr(result, "text", "") or "").strip()

    try:
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        if not text or "Internal Server Error" in text:
            raise ValueError("Invalid Gemini response")

        return _json.loads(text)

    except Exception:
        print("[gemini] JSON parse failed in extract_deadlines:", text[:200] if text else "EMPTY")
        return []           