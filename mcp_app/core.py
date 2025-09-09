from .config_loader import load_tools_config
from .ai_client import send_message, send_message_with_assistant
import json
from datetime import datetime
import os
from openai import OpenAI
import logging
import traceback
from django.http import JsonResponse
import time

logger = logging.getLogger('mcp_app')

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            encoded_object = obj.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        else:
            encoded_object =json.JSONEncoder.default(self, obj)
        return encoded_object

class MCPProcessor:
    def __init__(self):
        self.tools = load_tools_config()
        self.context_memory = []
        self.function_descriptions = self.generate_function_descriptions()
        self.client = OpenAI(api_key="")

    def generate_function_descriptions(self):
        # Esto podría ser automático leyendo signatures, para ahora es estático
        return [
            {
                "name": "get_demanda",
                "description": "Obtiene la demanda de un caso judicial.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "RIT": {"type": "string"},
                        "CORTE": {"type": "string"},
                        "Tribunal": {"type": "string"},
                    },
                    "required": ["RIT", "CORTE", "Tribunal"],
                }
            }
        ]

    def process_conversation(self, request, user_input):
        try:
            messages = [{"role": "user", "content": user_input}]
            ai_response = send_message_with_assistant(request, messages, functions=self.function_descriptions)
            logger.info(f"AI response: {ai_response}")

            return ai_response
        
        except Exception as e:
            logger.error(f"Error in process_conversation: {e}")
            logger.error(traceback.format_exc())
            return "Lo siento, ha ocurrido un error al procesar tu solicitud."