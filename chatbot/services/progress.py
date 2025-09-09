import uuid
from typing import Literal, Optional
from django.core.cache import cache

State = Literal[
    "queued",
    "gathering_context",
    "calling_llm",
    "streaming_answer",
    "done",
"error",
]

CACHE_PREFIX = "chatbot:progress:"
TTL_SECONDS = 60 * 10 # 10 minutos por defecto

def new_progress() -> str:
    key = str(uuid.uuid4())
    cache.set(CACHE_PREFIX + key, {"state": "queued"}, TTL_SECONDS)
    return key

def set_state(key: str, state: State, extra: Optional[dict] = None) -> None:
    data = {"state": state}
    if extra:
        data.update(extra)
    cache.set(CACHE_PREFIX + key, data, TTL_SECONDS)

def get_state(key: str) -> dict:
    return cache.get(CACHE_PREFIX + key, {"state": "error", "detail": "unknown key"})