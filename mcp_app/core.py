from .config_loader import load_tools_config
from .ai_client import send_message, send_message_with_assistant
import json
from datetime import datetime
import os
from openai import OpenAI
import logging
import traceback
from django.http import JsonResponse
import traceback

logger = logging.getLogger('mcp')

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
        #self.function_descriptions = self.generate_function_descriptions()
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
            },
            {
                "name": "get_competencias",
                "description": "Obtiene las competencias civiles de un tribunal en Chile a partir de su código.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tribunal_code": {"type": "string"}
                    },
                    "required": ["tribunal_code"],
                }
            },
            {
                "name": "get_cortes",
                "description": "Obtiene las cortes asociadas a una competencia",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "competencia": {
                            "type": "number",
                            "description": "id de la competencia"
                        }
                    },
                    "required": ["competencia"]
                }
            },
            {
                "name": "get_tribunales",
                "description": "Obtiene los tribunales asociados a una corte",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "corte": {
                            "type": "number",
                            "description": "id de la corte"
                        }
                    },
                    "required": ["corte"]
                }
            }
        ]

    def generate_function_descriptions_from_tools_list(self):
        #  tools_list.jso
        tools_file_path = os.path.join(os.path.dirname(__file__), 'tools_list.json')
        logger.info("Generating function descriptions from tools list at {}".format(tools_file_path))
        try:
            with open(tools_file_path, 'r') as f:
                tools_list = json.load(f)
            
            function_descriptions = []
            for tool in tools_list:
                function_description = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
                function_descriptions.append(function_description)
            
            logger.info(f"[core.generate_function_descriptions_from_tools_list] Generated function descriptions: {function_descriptions}")
            return function_descriptions
        except Exception as e:
            logger.error(f"[core.generate_function_descriptions_from_tools_list] Error generating function descriptions from tools list: {e}")
            logger.error(traceback.format_exc())
            return []

    def process_conversation(self, request, user_input, state):
        try:
            logger.info("[core.process_conversation] Loading tools list from tools_list.json")
            messages = [{"role": "user", "content": user_input}]
            ai_response = send_message_with_assistant(request, messages, functions=self.generate_function_descriptions_from_tools_list(), state=state)
            logger.info(f"[core.process_conversation] AI response: {ai_response}")

            return ai_response
        
        except Exception as e:
            logger.error(f"[core.process_conversation] Error: {e}")
            logger.error(traceback.format_exc())
            return "Lo siento, ha ocurrido un error al procesar tu solicitud."