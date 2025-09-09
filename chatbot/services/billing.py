import math
from dataclasses import dataclass
from typing import Optional
from django.conf import settings

# Configuración por defecto; se puede ajustar en settings.py del proyecto
ANON_LIMIT_PER_MINUTE = getattr(settings, "CHATBOT_ANON_LIMIT_PER_MINUTE", 3)
ANON_LIMIT_PER_DAY = getattr(settings, "CHATBOT_ANON_LIMIT_PER_DAY", 20)
REGISTERED_DAILY_QUOTA = getattr(settings, "CHATBOT_REGISTERED_DAILY_QUOTA", 200)
COST_PER_1K_TOKENS_USD = getattr(settings, "CHATBOT_COST_PER_1K_TOKENS_USD", 0.005)


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def estimated_cost_usd(self) -> float:
        return (self.total_tokens / 1000.0) * COST_PER_1K_TOKENS_USD


class BalanceService:
    """Servicio mock de saldo/consumo para usuarios registrados.
    En producción, reemplazar por integración con tu modelo de cuentas
    y facturación real.
    """
    def get_daily_quota(self, user) -> int:
        if user.is_authenticated:
            return REGISTERED_DAILY_QUOTA
        return ANON_LIMIT_PER_DAY

    def get_remaining_quota(self, user, used_today: int) -> int:
        return max(0, self.get_daily_quota(user) - used_today)

    def debit(self, user, usage: Usage) -> None:
        """Debita saldo según tokens usados.
        # TODO: Integrar con modelo real de cuentas/saldo.
        """
        pass

def estimate_usage_from_text(prompt: str, answer: str) -> Usage:
    # Estimación muy simple: ~1 token por 4 caracteres
    p = max(1, math.ceil(len(prompt) / 4))
    c = max(1, math.ceil(len(answer) / 4))
    return Usage(prompt_tokens=p, completion_tokens=c)