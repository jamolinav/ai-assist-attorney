from openai import OpenAI, BadRequestError
import time
import json
from datetime import datetime
from .config_loader import load_tools_config
import os
import traceback
import logging

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", None)
ASSISTANT_ID    = os.getenv("ASSISTANT_ID", None)

client  = OpenAI(api_key=OPENAI_API_KEY)
tools   = load_tools_config()

logger  = logging.getLogger('mcp')

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

def send_message_with_assistant(request, messages, functions, progress_key):
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

        try:
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=messages[-1]["content"]
            )
        except BadRequestError as e:
            msg = str(e)
            if "while a run" in msg and "is active" in msg:
                # Creamos nuevo thread y reintentamos una vez
                logger.warning(
                    f"[v1.2.1]; BadRequest por run activo en {thread.id}, "
                    f"creando nuevo thread y reintentando."
                )
                thread = client.beta.threads.create()
                request.session["openai_thread_id"] = thread.id

                client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=messages[-1]["content"]
                )
            else:
                raise

        logger.info(f"Mensaje enviado al thread {thread.id}, esperando respuesta...")

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            tools=[{"type": "function", "function": f} for f in functions],
        )

        # Espera a que el run termine (con timeout)
        MAX_WAIT = 180  # segundos máximo para esperar
        start_ts = time.time()

        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            logger.info(f"Estado del run: {run.status}")

            # 1) Estados finales
            if run.status in ["completed", "failed", "cancelled"]:
                logger.info(f"Run {run.id} terminado con estado: {run.status}")
                break

            # 2) El asistente requiere llamadas a herramientas
            if run.status == "requires_action":
                if not run.required_action or not run.required_action.submit_tool_outputs:
                    logger.error(f"Run {run.id} en requires_action pero sin submit_tool_outputs")
                    break

                tool_calls = run.required_action.submit_tool_outputs.tool_calls or []
                logger.info(f"Llamadas a herramientas requeridas: {tool_calls}")

                outputs = []
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    logger.info(f"Ejecutando función: {func_name}")

                    args = json.loads(tool_call.function.arguments or "{}")
                    args["user_id"] = request.user.id
                    logger.info(f"Argumentos: {args}")

                    func = tools.get(func_name)  # asumiendo dict global `tools`
                    if not func:
                        logger.error(f"Función {func_name} no encontrada en tools")
                        outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(
                                {"error": f"Función {func_name} no encontrada"},
                                cls=DateTimeEncoder,
                            ),
                        })
                        continue

                    args['progress_key'] = progress_key
                    result = func(args)
                    logger.info(f"[ai_client] Resultado de {func_name}: {result}")

                    outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result, cls=DateTimeEncoder),
                    })

                logger.info(f"Resultados de las funciones: {outputs}")

                # Enviar outputs de tools
                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=outputs,
                )

                # IMPORTANTE: aquí NO hacemos otro while interno.
                # Volvemos al inicio del mismo while para revisar el nuevo estado.
                continue

            # 3) Estados intermedios (queued / in_progress / otros no finales)
            if run.status not in ["queued", "in_progress"]:
                logger.error(f"Estado inesperado del run: {run.status}")
                break

            # 4) Timeout global
            elapsed = time.time() - start_ts
            if elapsed > MAX_WAIT:
                logger.error(f"Timeout esperando el run: {run.id} tras {elapsed:.1f}s")
                raise TimeoutError(f"Run {run.id} no terminó después de {MAX_WAIT} segundos")

            # Espera un poco antes de reintentar
            time.sleep(1)


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

