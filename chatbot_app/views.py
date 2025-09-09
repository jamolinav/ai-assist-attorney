import os
import json
import logging
import random
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from django.contrib.auth import login, authenticate

from .models import EmailVerification
from mcp_app.views import MCPProcessor
from django.views.decorators.http import require_POST

logger = logging.getLogger('chatbot_app')

@csrf_exempt
@require_POST
def procesar_causa(request):
    data = json.loads(request.body)
    # Aquí puedes hacer el procesamiento real con la causa
    logger.info(f"Causa recibida: {data}")
    return JsonResponse({"status": "ok"})

# 🔐 Registro de usuario con verificación de email
@csrf_exempt
def register_user(request):
    if request.method == "POST":
        print(request.POST)
        email = request.POST.get("email")
        nombre = request.POST.get("nombre")
        apellido = request.POST.get("apellido")
        codigo = request.POST.get("codigo")

        if not all([email, nombre, apellido, codigo]):
            messages.error(request, "Todos los campos son requeridos.")
            return redirect("chat")

        try:
            verif = EmailVerification.objects.get(email=email)
        except EmailVerification.DoesNotExist:
            messages.error(request, "Código no encontrado. Solicita uno nuevo.")
            return redirect("chat")

        if not verif.is_valid():
            verif.delete()
            messages.error(request, "Código expirado. Solicita uno nuevo.")
            return redirect("chat")

        if verif.code != codigo:
            messages.error(request, "Código incorrecto.")
            return redirect("chat")

        if User.objects.filter(username=email).exists():
            messages.info(request, "Ya existe una cuenta con ese correo.")

        # Temporizar validación correcta y redirigir a vista de contraseña
        request.session['registro_email'] = email
        request.session['registro_nombre'] = nombre
        request.session['registro_apellido'] = apellido

        verif.delete()

        return redirect('crear_password')

    elif request.method == "GET" and "email" in request.GET:
        email = request.GET.get("email").strip().lower()
        EmailVerification.objects.filter(email=email).delete()

        code = str(random.randint(100000, 999999))

        try:
            send_mail(
                subject='Tu código de verificación - Asistente Jurídico',
                message=f'Tu código para crear la cuenta es: {code}',
                from_email='no-reply@tuapp.com',
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Error al enviar correo: {e}")
            messages.error(request, "No se pudo enviar el correo. Intenta nuevamente.")
            return redirect("chat")

        EmailVerification.objects.create(email=email, code=code)
        return render(request, "chatbot/registro_confirmacion.html", {"email": email})

    return render(request, "chatbot/registro_inicio.html")


# 🧠 Vista del chat principal
def chat_view(request):
    context = {
        'version': settings.PJUD_VERSION,
        'asst_opciones': [
            {'id': 'asst_uNoMjJ2fWMgRm1wRXUj3JhjZ', 'nombre': 'Abogado Yo Liquido'}
        ],
        'is_superuser': request.user.is_superuser if request.user.is_authenticated else False
    }

    if request.user.is_authenticated:
        context['user_fullname'] = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

    return render(request, 'chatbot/chat.html', context)


# 📩 Envío de preguntas al asistente virtual
@csrf_exempt
#@login_required
def send_question(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        pregunta = request.POST.get('pregunta')
        asst_id = request.POST.get('asst_id')
        contexto_actual = request.session.get("contexto_extractores", {})

        logger.info(f"[send_question] Pregunta: {pregunta} - Asistente ID: {asst_id}")

        processor = MCPProcessor()
        respuesta = processor.process_conversation(request, pregunta)

        return JsonResponse({"response": {"respuesta": respuesta}})

    except Exception as e:
        logger.error(f"Error en send_question: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)

@csrf_exempt
def crear_password(request):
    email = request.session.get('registro_email')
    nombre = request.session.get('registro_nombre')
    apellido = request.session.get('registro_apellido')

    if not email:
        messages.error(request, "No tienes una sesión de registro válida.")
        return redirect('chat')

    if request.method == "POST":
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if not password or not password2:
            messages.error(request, "Debes ingresar y confirmar la contraseña.")
            return redirect('crear_password')

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('crear_password')

        if User.objects.filter(username=email).exists():
            messages.warning(request, "Ya existe una cuenta con este correo.")
            user = User.objects.get(username=email)
            user.set_password(password)
            user.save()
            messages.success(request, "Contraseña actualizada. Puedes iniciar sesión.")
            return redirect("login")

        # Crear usuario con contraseña válida
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellido
        )


        # Autenticación inmediata
        user = authenticate(username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Registro completo. Bienvenido/a.")
            return redirect("chat")
        else:
            messages.error(request, "Error al autenticar al nuevo usuario.")
            return redirect("login")

    # 👇 Aseguramos que GET siempre renderiza el formulario
    return render(request, "chatbot/crear_password.html", {"email": email})
