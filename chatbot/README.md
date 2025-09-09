# App Django: `chatbot` (ES-CL)

Frontend profesional con Bootstrap y backend mock listo para integrar con OpenAI y con el Poder Judicial.

## Instalación

1. Copia la carpeta `chatbot/` en tu proyecto Django.

2. En `settings.py` agrega:

```python
INSTALLED_APPS = [
    # ...
    'chatbot',
]

# Staticfiles (ajusta según tu despliegue)
STATIC_URL = '/static/'
# Si usas colecta de estáticos en producción
# STATIC_ROOT = BASE_DIR / 'staticfiles'
# Si tienes estáticos a nivel de proyecto
# STATICFILES_DIRS = [ BASE_DIR / 'static' ]

# Config opcional de límites:
CHATBOT_ANON_LIMIT_PER_MINUTE = 3
CHATBOT_ANON_LIMIT_PER_DAY = 20
CHATBOT_REGISTERED_DAILY_QUOTA = 200
CHATBOT_COST_PER_1K_TOKENS_USD = 0.005

# Cache (para throttling y progreso). Ejemplo simple en memoria:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'chatbot-cache',
    }
}
```

3. En `project/urls.py` incluye las rutas:

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path('chatbot/', include('chatbot.urls', namespace='chatbot')),
]
```

4. Variables de entorno (para integración futura con OpenAI):

```bash
export OPENAI_API_KEY="tu_api_key"
```

5. Migraciones: esta versión no define modelos, por lo que puedes correr directamente el servidor:

```bash
python manage.py collectstatic --noinput # si aplica
python manage.py runserver
```

## Uso

- **Home:** http://localhost:8000/chatbot/
- **Chat:** http://localhost:8000/chatbot/chat/
- **API:**
  - `POST /chatbot/api/send/` — `{"question": "..."}`
  - `GET /chatbot/api/progress/?key=<uuid>`

## Seguridad y cumplimiento (resumen)

- ✅ CSRF habilitado en POST.
- ✅ Validación básica de entrada.
- ✅ Privacidad: no se accede a causas sin consentimiento.
- ✅ Legal: Términos, Privacidad y Disclaimer incluidos (modales en `base.html`).
- ⚠️ Poder Judicial: considerar CAPTCHA/restricciones; proponer flujo legítimo con autenticación.
- 🔄 SSE/WebSockets: para procesos largos, reemplazar el polling por Server-Sent Events o WebSockets.

## Puntos de integración (TODO)

- **OpenAI** (`services/openai_client.py`): usar `OPENAI_API_KEY`, manejar usage/costos, timeouts, reintentos.
- **Causas PJUD**: módulo de autenticación y scraping/API; descarga de PDFs con registro de accesos.
- **Cuentas/Saldo** (`services/billing.py`): conectar a tu modelo y panel admin; métricas y logs.
- **i18n**: preparado `{% load i18n %}` y gettext en vistas; completar catálogo si sumas otros idiomas.
- **Observabilidad**: agregar logging estructurado y métricas (latencia, tasas de error) según tu stack.

## Tests

Ejecuta:

```bash
python manage.py test chatbot
```

Incluye pruebas básicas de rutas, envío y rate limiting.

## Accesibilidad

- ♿ HTML semántico, roles ARIA y foco visible.
- 🎨 Contraste alto y tamaños accesibles en CSS.

## Notas de despliegue

- ⚙️ Configura un backend de cache compartido (Memcached/Redis) en producción para que throttling y progreso funcionen en múltiples instancias.
- 📂 Ejecuta collectstatic y sirve estáticos con tu servidor/aplicación (Whitenoise, CDN, etc.).