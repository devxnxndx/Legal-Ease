import asyncio
import time

ANALYSIS_LOCK = asyncio.Lock()

_CHAT_ACTIVE = 0
_LAST_CHAT_ACTIVITY = 0.0


def chat_started() -> None:
    global _CHAT_ACTIVE, _LAST_CHAT_ACTIVITY
    _CHAT_ACTIVE += 1
    _LAST_CHAT_ACTIVITY = time.monotonic()


def chat_ping() -> None:
    global _LAST_CHAT_ACTIVITY
    _LAST_CHAT_ACTIVITY = time.monotonic()


def chat_finished() -> None:
    global _CHAT_ACTIVE, _LAST_CHAT_ACTIVITY
    _CHAT_ACTIVE = max(0, _CHAT_ACTIVE - 1)
    _LAST_CHAT_ACTIVITY = time.monotonic()


async def wait_for_chat_idle(
    idle_seconds: int = 15,
    poll_seconds: float = 1.5,
    max_wait_seconds: int = 120,
) -> bool:
    start = time.monotonic()

    while True:
        now = time.monotonic()
        idle_for = (now - _LAST_CHAT_ACTIVITY) if _LAST_CHAT_ACTIVITY else float("inf")

        if _CHAT_ACTIVE == 0 and idle_for >= idle_seconds:
            return True

        if now - start >= max_wait_seconds:
            return False

        await asyncio.sleep(poll_seconds)