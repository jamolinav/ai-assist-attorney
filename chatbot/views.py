import json
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie, csrf_protect
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from .forms import ChatForm
from .utils.rate_limit import get_client_ip, check_and_increment_anon, get_daily_used_for_ip
from .services import billing
from .services.openai_client import generate_answer
from .services.progress import new_progress, set_state, get_state


@require_GET
@ensure_csrf_cookie
def home_view(request: HttpRequest) -> HttpResponse:
    # Datos de límites visibles en UI
    ip = get_client_ip(request)
    used_today = get_daily_used_for_ip(ip)
    daily_quota = billing.BalanceService().get_daily_quota(request.user)
    remaining = max(0, daily_quota - used_today)
    return render(request, "chatbot/home.html", {
        "remaining_today": remaining,
        "daily_quota": daily_quota,
    })


@require_GET
@ensure_csrf_cookie
def chat_view(request: HttpRequest) -> HttpResponse:
    form = ChatForm()
    return render(request, "chatbot/chat.html", {"form": form})


@require_POST
@csrf_protect
def api_send(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        question = (payload.get("question") or "").strip()
        if not question:
            return JsonResponse(
                {"status": "error", "message": "La pregunta es obligatoria."}, 
                status=400
            )
        
        ip = get_client_ip(request)
        # 1) Throttling anónimos
        if not request.user.is_authenticated:
            rl = check_and_increment_anon(ip)
            if not rl["allowed"]:
                return JsonResponse({
                    "status": "rate_limited",
                    "message": (
                        "Has alcanzado el límite de consultas. Inténtalo más "
                        "tarde o crea una cuenta."
                    ),
                    "limits": rl,
                }, status=429)
            limits = rl
        else:
            # Usuarios registrados: mock de cuota/saldo
            used_today = get_daily_used_for_ip(ip)  # En producción, medir por usuario
            bs = billing.BalanceService()
            remaining = bs.get_remaining_quota(request.user, used_today)
            if remaining <= 0:
                return JsonResponse({
                    "status": "rate_limited",
                    "message": "No te quedan consultas hoy con tu plan actual.",
                    "limits": {"minute_left": 0, "day_left": 0},
                }, status=402)
            # Incremento de uso diario compartido por IP (simple)
            check_and_increment_anon(ip)
            limits = {"minute_left": None, "day_left": remaining - 1}
        
        # 2) Crear progreso
        progress_key = new_progress()
        set_state(progress_key, "gathering_context")
        
        # 3) Preparar contexto del usuario (mock)
        user_context = {
            "user_id": request.user.id if request.user.is_authenticated else None,
            # TODO: Adjuntar consentimiento para acceder a causas
            # TODO: Incluir flags/IDs de causas propias si fue autorizado
        }
        
        set_state(progress_key, "calling_llm")
        # 4) Llamada mock a OpenAI
        answer = generate_answer(question, user_context)
        
        set_state(progress_key, "streaming_answer")
        # 5) Estimar usage/costo y debitar si aplica
        usage = billing.estimate_usage_from_text(question, answer)
        if request.user.is_authenticated:
            billing.BalanceService().debit(request.user, usage)
        
        set_state(progress_key, "done")
        return JsonResponse({
            "status": "ok",
            "message": answer,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "estimated_cost_usd": round(usage.estimated_cost_usd(), 6),
            },
            "limits": limits,
            "progress_key": progress_key,
        })
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=500
        )


@require_GET
def api_progress(request: HttpRequest) -> JsonResponse:
    key = request.GET.get("key")
    if not key:
        return JsonResponse(
            {"status": "error", "message": "Falta parámetro 'key'."},
            status=400
        )
    state = get_state(key)
    return JsonResponse({"status": "ok", "progress": state})
