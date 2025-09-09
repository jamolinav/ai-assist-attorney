import datetime
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

# Valores por defecto (configurables en settings.py)
ANON_LIMIT_PER_MINUTE = getattr(settings, "CHATBOT_ANON_LIMIT_PER_MINUTE", 3)
ANON_LIMIT_PER_DAY = getattr(settings, "CHATBOT_ANON_LIMIT_PER_DAY", 20)

def _seconds_until_midnight() -> int:
    now = timezone.localtime()
    tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0,
    second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())

def get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")

def check_and_increment_anon(ip: str) -> dict:
    """Devuelve {allowed: bool, minute_left: int, day_left: int} y aumenta contadores."""
    # Por minuto
    m_key = f"rl:{ip}:m"
    m = cache.get(m_key, 0)
    if m >= ANON_LIMIT_PER_MINUTE:
        return {"allowed": False, "minute_left": 0, "day_left": 0}
    cache.set(m_key, m + 1, timeout=60)

    # Por día
    d_key = f"rl:{ip}:d"
    d = cache.get(d_key, 0)
    if d >= ANON_LIMIT_PER_DAY:
        return {"allowed": False, "minute_left": ANON_LIMIT_PER_MINUTE - (m + 1), "day_left": 0}
    cache.set(d_key, d + 1, timeout=_seconds_until_midnight())
    return {
        "allowed": True,
        "minute_left": max(0, ANON_LIMIT_PER_MINUTE - (m + 1)),
        "day_left": max(0, ANON_LIMIT_PER_DAY - (d + 1)),
    }


def get_daily_used_for_ip(ip: str) -> int:
    d_key = f"rl:{ip}:d"
    return cache.get(d_key, 0)