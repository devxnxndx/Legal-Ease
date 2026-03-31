import glob
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple


# Gemini's multimodal API accepts these natively (including webm)
SUPPORTED_GEMINI_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/mpeg",
    "audio/aiff",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
}

MIME_SUFFIX_MAP = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/aiff": ".aiff",
    "audio/x-aiff": ".aiff",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
}


def _canonical_mime_type(mime_type: str) -> str:
    mime = (mime_type or "").split(";")[0].strip().lower()

    if mime in {"audio/x-wav"}:
        return "audio/wav"
    if mime in {"audio/mp3"}:
        return "audio/mpeg"
    if mime in {"audio/x-aiff"}:
        return "audio/aiff"
    # Treat video/webm as audio/webm for Gemini
    if mime == "video/webm":
        return "audio/webm"

    return mime


# ---------------------------------------------------------------------------
# ffmpeg discovery — cached after first lookup
# ---------------------------------------------------------------------------
_ffmpeg_path: str | None = None
_ffmpeg_searched = False


def _find_ffmpeg() -> str | None:
    """
    Locate the ffmpeg executable.  Search order:
      1. FFMPEG_PATH environment variable (explicit override)
      2. System PATH  (``where ffmpeg`` / ``which ffmpeg``)
      3. Common Windows install locations (WinGet, Chocolatey, Scoop)
    Returns the full path string or None.
    """
    global _ffmpeg_path, _ffmpeg_searched
    if _ffmpeg_searched:
        return _ffmpeg_path
    _ffmpeg_searched = True

    # 1. Explicit env var
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        _ffmpeg_path = env_path
        print(f"[audio_convert] Using ffmpeg from FFMPEG_PATH: {_ffmpeg_path}")
        return _ffmpeg_path

    # 2. Already on PATH?
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            _ffmpeg_path = "ffmpeg"
            print("[audio_convert] Found ffmpeg on system PATH")
            return _ffmpeg_path
    except FileNotFoundError:
        pass

    # 3. Common Windows install locations
    local_app_data = os.getenv("LOCALAPPDATA", "")
    home = os.getenv("USERPROFILE", "")

    search_patterns = [
        # WinGet (Gyan.FFmpeg)
        os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "ffmpeg-*", "bin", "ffmpeg.exe"),
        # Chocolatey
        os.path.join(os.getenv("ChocolateyInstall", r"C:\ProgramData\chocolatey"), "bin", "ffmpeg.exe"),
        # Scoop
        os.path.join(home, "scoop", "shims", "ffmpeg.exe"),
        os.path.join(home, "scoop", "apps", "ffmpeg", "current", "bin", "ffmpeg.exe"),
        # Manual installs
        os.path.join("C:\\", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.getenv("ProgramFiles", r"C:\Program Files"), "ffmpeg", "bin", "ffmpeg.exe"),
    ]

    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            _ffmpeg_path = matches[0]
            print(f"[audio_convert] Auto-discovered ffmpeg at: {_ffmpeg_path}")
            return _ffmpeg_path

    print("[audio_convert] WARNING: ffmpeg not found anywhere. Audio conversion disabled.")
    return None


def convert_to_wav(audio_bytes: bytes, input_suffix: str = ".webm") -> bytes:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed or not discoverable.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{input_suffix}"
        output_path = tmpdir_path / "output.wav"

        input_path.write_bytes(audio_bytes)

        command = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"ffmpeg not found at '{ffmpeg}'. Set FFMPEG_PATH in .env."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip()}")

        return output_path.read_bytes()


def normalize_audio_for_gemini(audio_bytes: bytes, mime_type: str) -> Tuple[bytes, str]:
    mime = _canonical_mime_type(mime_type)

    if mime in SUPPORTED_GEMINI_AUDIO_MIME_TYPES:
        return audio_bytes, mime

    # Try to convert with ffmpeg; if ffmpeg is missing, pass raw audio
    # through and let Gemini handle it (it's often more flexible than the
    # official docs suggest).
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print(
            f"[audio_convert] ffmpeg not available — sending raw {mime} to Gemini "
            "(conversion skipped)"
        )
        fallback_mime = "audio/webm" if "webm" in mime or "video" in mime else mime
        return audio_bytes, fallback_mime

    input_suffix = MIME_SUFFIX_MAP.get(mime, ".bin")
    try:
        wav_bytes = convert_to_wav(audio_bytes, input_suffix=input_suffix)
        return wav_bytes, "audio/wav"
    except RuntimeError as e:
        print(f"[audio_convert] ffmpeg conversion failed: {e} — sending raw audio")
        return audio_bytes, mime