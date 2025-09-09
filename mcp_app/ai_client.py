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
            # Si ya existe, lo reutiliza
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

        # Añade el mensaje al thread
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

        # Espera a que el run termine
        MAX_WAIT = 30  # segundos máximo para esperar
        waited = 0

        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            logger.info(f"Estado del run: {run.status}")
            
            if run.status in ["completed", "failed", "cancelled"]:
                break
            elif run.status not in ["queued", "in_progress", "requires_action"]:
                logger.error(f"Estado inesperado del run: {run.status}")
                break

            time.sleep(2)
            waited += 2
            if waited > MAX_WAIT:
                logger.error(f"Timeout esperando el run: {run.id}")
                raise TimeoutError(f"Run {run.id} no terminó después de {MAX_WAIT} segundos")

            if run.status == "requires_action":
                # Obtener las llamadas a herramientas (funciones) requeridas
                tool_calls = run.required_action.submit_tool_outputs.tool_calls

                outputs = []
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    logger.info(f"Ejecutando función: {func_name}")
                    args = json.loads(tool_call.function.arguments)
                    args["user_id"] = request.user.id
                    logger.info(f"Argumentos: {args}")
                    func = tools.get(func_name)
                    result = func(args)  # ejecuta tu función real con los parámetros dados
                    outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result, cls=DateTimeEncoder)
                    })

                logger.info(f"Resultados de las funciones: {outputs}")
                # Enviar las respuestas de las funciones al Assistant
                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=outputs
                )

                logger.info(f"Estado del run después de enviar resultados: {run.status}")
                # Espera nuevamente a que finalice la ejecución
                while True:
                    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                    logger.info(f"Estado del run: {run.status}")
                    if run.status == "completed":
                        break
                    time.sleep(1)  # espera un poco antes de volver a consultar

        # Recupera el mensaje final del assistant
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        logger.info(f"Mensajes en el thread: {messages}")

        last_message = messages.data[0]

        # Devuelve el mensaje como un objeto estándar para que lo puedas interpretar igual que con chat.completions
        response = {
            "choices": [
                {
                    "message": {
                        "role": last_message.role,
                        "content": last_message.content[0].text.value
                    }
                }
            ]
        }
        logger.info(f"Respuesta final: {response}")

        return last_message.content[0].text.value

    except Exception as e:
        logger.error(f"Error en send_message_with_assistant: {e}")
        logger.error(f"Detalles del error: {traceback.format_exc()}")
        # Manejo de errores: puedes devolver un mensaje de error o un objeto vacío
        return {
            "choices": [
                {
                    "message": {
                        "content": "Lo siento, ha ocurrido un error al procesar tu solicitud."
                    }
                }
            ]
        }
