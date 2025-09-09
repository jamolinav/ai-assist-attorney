from django.core.mail import send_mail
import random

def enviar_codigo_verificacion(email):
    code = f"{random.randint(100000, 999999)}"
    send_mail(
        subject='Código de verificación - Asistente Jurídico',
        message=f'Tu código de verificación es: {code}',
        from_email='no-reply@tuapp.com',
        recipient_list=[email],
        fail_silently=False,
    )
    return code
