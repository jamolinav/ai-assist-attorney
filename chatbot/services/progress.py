import uuid
from pjud.celeryy import app
from typing import Literal, Optional
from django.core.cache import cache
import logging, traceback

logger = logging.getLogger('general')

State = Literal[
    "queued",
    "gathering_context",
    "calling_llm",
    "streaming_answer",
    "done",
    "error",
    "obteniendo_demanda",
    "no_pjud_info_available_yet",
]

CACHE_PREFIX = "chatbot:progress:"
TTL_SECONDS = 60 * 10 # 10 minutos por defecto

def new_progress() -> str:
    key = str(uuid.uuid4())
    print(f"Creating new progress tracker with key: {key}")
    cache.set(CACHE_PREFIX + key, {"state": "queued"}, TTL_SECONDS)
    print(f"Created new progress tracker with key: {key}")
    logger.info(f"Created new progress tracker with key: {key}")
    return key

@app.task(queue="pjud_azure")
def set_state(key: str, state: State, extra: Optional[dict] = None) -> None:
    logger.info(f"Setting state for key {key} to {state} with extra: {extra}")
    data = {"state": state}
    if extra:
        data.update(extra)
    cache.set(CACHE_PREFIX + key, data, TTL_SECONDS)

def get_state(key: str) -> dict:
    state = cache.get(CACHE_PREFIX + key, {"state": "error", "detail": "unknown key"})
    logger.debug(f"Retrieved state for key {key}: {state}")
    return state