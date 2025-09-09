from openai import OpenAI
import time
import json
from datetime import datetime
from .config_loader import load_tools_config
import os
import traceback
import logging
from django.http import JsonResponse

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", None)
ASSISTANT_ID    = os.getenv("ASSISTANT_ID", None)

client  = OpenAI(api_key=OPENAI_API_KEY)
tools   = load_tools_config()

logger  = logging.getLogger('mcp_app')

def send_message(messages, functions=None, assistant_id=None):
    respuesta = client.chat.completions.create(
        #model="gpt-3.5-turbo",  # Usamos GPT-3.5 para este ejemplo
        model="gpt-4",
        functions=functions,
        function_call="auto",
        messages=messages,
        max_tokens=500,
        temperature=0.5,
    )
    return respuesta

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

def send_message_with_assistant(request, messages, functions):
    try:
        # Revisa si ya existe un thread en la sesión
        thread_id = request.session.get("openai_thread_id")
        thread = None

        if thread_id:
            try:
                thread = client.beta.threads.retrieve(thread_id)
                logger.info(f"Reutilizando thread existente: {thread_id}")
            except Exception as e:
                logger.error(f"Error al reutilizar thread: {e}")

        if not thread:
            # Si no existe, crea uno nuevo y lo guarda en sesión
            thread = client.beta.threads.create()
            request.session["openai_thread_id"] = thread.id
            logger.info(f"Creado nuevo thread: {thread.id}")

        # Añade el último mensaje del usuario al thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=messages[-1]["content"]
        )

        # Ejecuta un run con funciones disponibles
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            tools=[{"type": "function", "function": f} for f in functions],
        )

        # Espera a que el run termine (con timeout)
        MAX_WAIT = 180  # segundos máximo para esperar
        waited = 0

        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            logger.info(f"Estado del run: {run.status}")

            if run.status in ["completed", "failed", "cancelled"]:
                break

            if run.status not in ["queued", "in_progress", "requires_action"]:
                logger.error(f"Estado inesperado del run: {run.status}")
                break

            if run.status == "requires_action":
                # Obtener y ejecutar llamadas a herramientas (funciones)
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                outputs = []
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    logger.info(f"Ejecutando función: {func_name}")
                    args = json.loads(tool_call.function.arguments)
                    args["user_id"] = request.user.id
                    logger.info(f"Argumentos: {args}")
                    func = tools.get(func_name)
                    result = func(args)
                    outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result, cls=DateTimeEncoder)
                    })

                logger.info(f"Resultados de las funciones: {outputs}")

                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=outputs
                )

                # Espera nuevamente a que finalice la ejecución
                inner_waited = 0
                while True:
                    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                    logger.info(f"Estado del run: {run.status}")
                    if run.status in ["completed", "failed", "cancelled"]:
                        break
                    time.sleep(1)
                    inner_waited += 1
                    if waited + inner_waited > MAX_WAIT:
                        logger.error(f"Timeout esperando el run tras tools: {run.id}")
                        raise TimeoutError(f"Run {run.id} no terminó después de {MAX_WAIT} segundos")
                # Acumula el tiempo de espera interno
                waited += inner_waited

            # Espera incremental cuando no hay requires_action
            if run.status in ["queued", "in_progress"]:
                time.sleep(2)
                waited += 2
                if waited > MAX_WAIT:
                    logger.error(f"Timeout esperando el run: {run.id}")
                    raise TimeoutError(f"Run {run.id} no terminó después de {MAX_WAIT} segundos")

        # Recupera los mensajes del thread
        thread_messages = client.beta.threads.messages.list(thread_id=thread.id)
        logger.info(f"Mensajes en el thread: {thread_messages}")

        # Intenta encontrar el último mensaje del assistant con contenido de texto
        assistant_role = "assistant"
        content_text = None

        for msg in thread_messages.data:
            if getattr(msg, "role", "") == "assistant":
                try:
                    # Busca el primer bloque de tipo text
                    for block in getattr(msg, "content", []) or []:
                        if getattr(block, "type", "") == "text":
                            value = getattr(block.text, "value", None)
                            if isinstance(value, str) and value.strip():
                                content_text = value
                                break
                    if content_text:
                        assistant_role = msg.role
                        break
                except Exception:
                    # Si algo falla, sigue buscando otros mensajes
                    pass

        # Fallback si no encontramos texto (p.ej. solo tool_outputs/imágenes)
        if not content_text:
            content_text = "No se encontró una respuesta de texto del asistente."
            # Si el run falló, refleja mejor el estado
            if getattr(run, "status", "") == "failed":
                content_text = "La ejecución del asistente falló al generar una respuesta."

        # Construye SIEMPRE la respuesta normalizada tipo chat.completions
        response = {
            "choices": [
                {
                    "message": {
                        "role": assistant_role,
                        "content": content_text
                    }
                }
            ]
        }

        logger.info(f"Respuesta final normalizada: {response}")
        return response

    except Exception as e:
        logger.error(f"Error en send_message_with_assistant: {e}")
        logger.error(f"Detalles del error: {traceback.format_exc()}")
        # Devuelve SIEMPRE dict normalizado en errores
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Lo siento, ha ocurrido un error al procesar tu solicitud."
                    }
                }
            ]
        }

