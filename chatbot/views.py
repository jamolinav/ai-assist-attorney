import json
import logging
import traceback
import time
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
from mcp_app.views import MCPProcessor
# import settings to get version
from django.conf import settings

# Configuración del logger
logger = logging.getLogger('chatbot')

VERSION = settings.PJUD_VERSION
print("Chatbot version:", VERSION)

@require_GET
@ensure_csrf_cookie
def home_view(request: HttpRequest) -> HttpResponse:
    """Vista principal de la página de inicio del chatbot"""
    try:
        logger.info(f"Home view accessed by user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
        
        # Datos de límites visibles en UI
        ip = get_client_ip(request)
        used_today = get_daily_used_for_ip(ip)
        daily_quota = billing.BalanceService().get_daily_quota(request.user)
        remaining = max(0, daily_quota - used_today)
        
        logger.debug(f"Quota info - IP: {ip}, Used: {used_today}, Quota: {daily_quota}, Remaining: {remaining}")
        
        return render(request, "chatbot/home.html", {
            "remaining_today": remaining,
            "daily_quota": daily_quota,
            "PJUD_VERSION": settings.PJUD_VERSION,
        })
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Error rendering home view: {str(e)}\n{tb_str}")
        return render(request, "chatbot/home.html", {"error": "Error al cargar la página de inicio."})


@require_GET
@ensure_csrf_cookie
def chat_view(request: HttpRequest) -> HttpResponse:
    """Vista de la interfaz de chat"""
    try:
        logger.info(f"Chat view accessed by user: {request.user.username if request.user.is_authenticated else 'Anonymous'} from IP: {get_client_ip(request)}")
        form = ChatForm()
        return render(request, "chatbot/chat.html", {"form": form})
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Error rendering chat view: {str(e)}\n{tb_str}")
        return render(request, "chatbot/chat.html", {"error": "Error al cargar la interfaz de chat."})


@require_POST
@csrf_protect
def api_send(request: HttpRequest) -> JsonResponse:
    """API para enviar preguntas al chatbot"""
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"
    
    try:
        logger.info(f"[{request_id}] New API request received from IP: {get_client_ip(request)}")
        
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        question = (payload.get("question") or "").strip()
        if not question:
            logger.warning(f"[{request_id}] Empty question received")
            return JsonResponse(
                {"status": "error", "message": "La pregunta es obligatoria."}, 
                status=400
            )
        
        # Truncar pregunta en logs para evitar exponer datos sensibles
        safe_question = question[:50] + ("..." if len(question) > 50 else "")
        logger.info(f"[{request_id}] Question received: {safe_question}")
        
        ip = get_client_ip(request)
        # 1) Throttling anónimos
        if not request.user.is_authenticated:
            logger.debug(f"[{request_id}] Processing anonymous user request")
            rl = check_and_increment_anon(ip)
            if not rl["allowed"]:
                logger.warning(f"[{request_id}] Rate limit exceeded for IP: {ip}")
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
            logger.debug(f"[{request_id}] Processing authenticated user request: {request.user.username}")
            used_today = get_daily_used_for_ip(ip)  # En producción, medir por usuario
            bs = billing.BalanceService()
            remaining = bs.get_remaining_quota(request.user, used_today)
            logger.debug(f"[{request_id}] User quota - Used: {used_today}, Remaining: {remaining}")
            
            if remaining <= 0:
                logger.warning(f"[{request_id}] User {request.user.username} has no remaining quota")
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
        logger.debug(f"[{request_id}] Created progress tracker with key: {progress_key}")
        set_state(progress_key, "gathering_context")
        
        # 3) Preparar contexto del usuario (mock)
        user_context = {
            "user_id": request.user.id if request.user.is_authenticated else None,
            # TODO: Adjuntar consentimiento para acceder a causas
            # TODO: Incluir flags/IDs de causas propias si fue autorizado
        }
        logger.debug(f"[{request_id}] User context prepared: {user_context}")
        
        set_state(progress_key, "calling_llm")
        # 4) Llamada mock a OpenAI
        logger.info(f"[{request_id}] Calling MCP processor")
        try:
            processor = MCPProcessor()
            state = {"progress_key": 'starting'}
            response = processor.process_conversation(request, question, progress_key)
            logger.debug(f"[{request_id}] MCP processor response: {response}")
            # E.G.: {'choices': [{'message': {'role': 'assistant', 'content': '¡Hola! ¿En qué puedo ayudarte hoy con respecto a alguna demanda o trámite judicial?'}}]}
            answer = response.get('choices', [{}])[0].get('message', {}).get('content', 'Error: no response')
            logger.debug(f"[{request_id}] MCP processor response received")
        except Exception as e:
            logger.error(f"[{request_id}] Error calling MCP processor: {str(e)}", exc_info=True)
            answer = "Lo siento, ocurrió un error al procesar tu consulta."

        set_state(progress_key, "streaming_answer")
        # 5) Estimar usage/costo y debitar si aplica
        logger.info(f"[{request_id}] Answer generated successfully, length: {len(answer)} chars")
        usage = billing.estimate_usage_from_text(question, answer)
        logger.debug(f"[{request_id}] Usage estimation: {usage.total_tokens} tokens, cost: ${usage.estimated_cost_usd()}")
        
        if request.user.is_authenticated:
            try:
                billing.BalanceService().debit(request.user, usage)
                logger.info(f"[{request_id}] User {request.user.username} debited for {usage.total_tokens} tokens")
            except Exception as e:
                logger.error(f"[{request_id}] Error in billing: {str(e)}", exc_info=True)
        
        print(f"state: {state['progress_key']}")  # Debug del estado actual
        if 'get_demanda' in state['progress_key']:
            set_state(progress_key, "obteniendo_demanda")
        else:
            set_state(progress_key, "done")

        process_time = time.time() - start_time
        logger.info(f"[{request_id}] Request completed in {process_time:.2f}s")
        
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
        logger.error(f"[{request_id}] Unhandled exception in api_send: {str(e)}", exc_info=True)
        tb_str = traceback.format_exc()
        logger.error(f"[{request_id}] Traceback: {tb_str}")
        return JsonResponse(
            {"status": "error", "message": "Ha ocurrido un error inesperado. Por favor, intenta nuevamente."},
            status=500
        )


@require_GET
def api_progress(request: HttpRequest) -> JsonResponse:
    """API para consultar el progreso de una consulta en curso"""
    key = request.GET.get("key")
    ip = get_client_ip(request)
    
    logger.info(f"Progress check from IP: {ip} for key: {key}")
    print(f"Progress check for key: {key} from IP: {ip}")
    
    if not key:
        logger.warning(f"Missing 'key' parameter in progress check from IP: {ip}")
        return JsonResponse(
            {"status": "error", "message": "Falta parámetro 'key'."},
            status=400
        )
    
    try:
        state = get_state(key)
        logger.debug(f"Progress state for key {key}: {state}")
        return JsonResponse({"status": "ok", "progress": state})
    except Exception as e:
        logger.error(f"Error retrieving progress for key {key}: {str(e)}", exc_info=True)
        tb_str = traceback.format_exc()
        logger.error(f"Traceback: {tb_str}")
        return JsonResponse(
            {"status": "error", "message": "Error al consultar progreso."},
            status=500
        )
