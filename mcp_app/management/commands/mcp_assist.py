import logging
from django.core.management.base import BaseCommand
import json
from mcp_app.core import MCPProcessor

logger = logging.getLogger('mcp')

class Command(BaseCommand):
    help = "Eres un agente AI que usa herramientas MCP para responder preguntas."
    def add_arguments(self, parser):
        parser.add_argument(
            "--args",
            dest="args_json",
            type=str,
            default="{}",
            help="JSON con los argumentos a pasar a la tool"
        )
    def handle(self, *args, **options):
        arguments = json.loads(options['args_json']) if options['args_json'] else {}
        question = arguments.get('question', '¿Cuál es la capital de Francia?')
        
        #simular request Django
        '''
        2025-10-27 15:12:28,434 [ERROR] - [v1.2.1]; Detalles del error: Traceback (most recent call last):
            File "/Users/juanmolina/Documents/Github/ai-assist-attorney/mcp_app/ai_client.py", line 42, in send_message_with_assistant
                thread_id = request.session.get("openai_thread_id")
            AttributeError: 'DummyRequest' object has no attribute 'session'
        '''
        request = type('DummyRequest', (), {})()
        request.session = {}
        request.user = type('DummyUser', (), {})()
        request.user.id = 1

        processor = MCPProcessor()
        final_response = processor.process_conversation(request, question)

        logger.info(f"Final response: {final_response}")

        print(final_response)
    
