from django.shortcuts import render
from django.http import JsonResponse
from .core import MCPProcessor
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from rest_framework import permissions

# Configuración del logger
logger = logging.getLogger('mcp')

# Create your views here.
class MCPEndpoint(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def __init__(self):
        self.processor = MCPProcessor()

    def post(self, request):
        user_input = request.data.get('message')
        logger.info(f"Received user input: {user_input}")

        # Paso 1: usar funciones dinámicas
        final_response = self.processor.process_conversation(user_input)

        logger.info(f"Final response: {final_response}")
        return JsonResponse({"respuesta": final_response})

