"""
ASGI config for pjud project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
import time
import logging
import traceback
from contextlib import asynccontextmanager
from mcp_app.tools import call_tool_async

from django.core.asgi import get_asgi_application

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp.server.fastmcp import FastMCP
from mcp_app.tools import register_tools

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pjud.settings')

# Configurar logger
logger = logging.getLogger('general')

# 1) Django ASGI
logger.info("Inicializando Django ASGI application")
django_asgi = get_asgi_application()

# 2) MCP Server (FastMCP) - Create a simple wrapper
APP_NAME = os.getenv("APP_NAME", "mcp-django")
logger.info(f"Creando servidor MCP FastMCP con nombre: {APP_NAME}")
mcp = FastMCP(APP_NAME)
logger.info("Registrando herramientas MCP")
register_tools(mcp)
logger.info("Servidor MCP inicializado correctamente")

# Create a clean MCP endpoint function using tools.py
async def mcp_endpoint(request):
    from starlette.responses import JSONResponse, Response, PlainTextResponse
    from mcp_app.tools import get_tools_list, call_tool
    import json

    # --- util seguro para parsear body (puede venir vacío en notifs) ---
    async def safe_payload(req):
        body = await req.body()
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    # ---- GET (por si el cliente intenta abrir SSE en /mcp) ----
    if request.method == "GET":
        logger.debug("Recibida petición GET en endpoint MCP")
        # Si no implementas SSE aún, responde 200 texto vacío (NO JSON)
        return PlainTextResponse("", status_code=200)

    # ---- OPTIONS (preflight CORS) ----
    if request.method == "OPTIONS":
        logger.debug("Recibida petición OPTIONS (CORS preflight)")
        return Response(status_code=204)

    try:
        data = await safe_payload(request)
        method = data.get("method")
        request_id = data.get("id")

        logger.info(f"Petición MCP recibida - Método: {method}, ID: {request_id}")
        logger.debug(f"Datos completos de la petición: {data}")

        # 1) NOTIFICATIONS: NUNCA JSON-RPC de vuelta
        if isinstance(method, str) and (
            method == "initialized" or method.startswith("notifications/")
        ):
            logger.info(f"Procesando notificación MCP: {method}")
            # 204 sin body (o 200 texto vacío si tu proxy es quisquilloso)
            return Response(status_code=204)

        # 2) initialize -> respuesta JSON-RPC válida
        if method == "initialize":
            logger.info("Procesando inicialización del servidor MCP")
            available_tools = get_tools_list()
            logger.info(f"Servidor inicializado con {len(available_tools)} herramientas disponibles")

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        # Solo un dict; evita campos no estandar como "count"
                        "tools": {"listChanged": True},
                        # si no implementas estas capacidades, puedes omitirlas o dejarlas vacías
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {"name": "mcp-django", "version": "1.0.0"}
                }
            })

        # 3) tools/list -> lista (array) de tools
        if method == "tools/list" or method == "prompts/list":
            logger.info(f"Solicitada lista de herramientas - Método: {method}")
            tools_list = get_tools_list()
            logger.info(f"Devolviendo {len(tools_list)} herramientas disponibles")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools_list}
            }, status_code=200)

        # 4) tools/call
        if method == "XXXtools/call":
            params = data.get("params") or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Ejecutando herramienta: {tool_name}")
            logger.debug(f"Argumentos de la herramienta: {arguments}")
            
            try:
                result = call_tool(tool_name, arguments)
                logger.info(f"Herramienta {tool_name} ejecutada exitosamente")
                logger.debug(f"Resultado de la herramienta: {result}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                })
            except Exception as e:
                logger.error(f"Error ejecutando herramienta {tool_name}: {str(e)}")
                logger.error(f"Traceback completo:\n{traceback.format_exc()}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": str(e)}
                })
            
        if method == "tools/call":
            params = data.get("params") or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"Ejecutando herramienta: {tool_name}")
            logger.debug(f"Argumentos de la herramienta: {arguments}")

            try:
                result = await call_tool_async(tool_name, arguments)  # <-- AWAIT AQUÍ
                logger.info(f"Herramienta {tool_name} ejecutada exitosamente")
                logger.debug(f"Resultado de la herramienta: {result}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                })
            except Exception as e:
                logger.error(f"Error ejecutando herramienta {tool_name}: {str(e)}")
                logger.error(f"Traceback completo:\n{traceback.format_exc()}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": str(e)}
                })

        # 5) shutdown (request de cierre: SÍ espera JSON-RPC)
        if method == "shutdown":
            logger.info("Solicitud de cierre del servidor MCP recibida")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            })

        # 6) Invalid Request (sin método)
        if method is None:
            logger.warning(f"Petición inválida recibida - Falta método. Request ID: {request_id}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32600, "message": "Invalid Request: missing 'method' or 'jsonrpc'."}
            }, status_code=400)

        # 7) Método desconocido
        logger.warning(f"Método desconocido solicitado: {method}, Request ID: {request_id}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }, status_code=404)

    except Exception as e:
        # Si algo se rompe, devuelve JSON-RPC error (no {})
        logger.critical(f"Error interno del servidor MCP: {str(e)}")
        logger.critical(f"Traceback completo:\n{traceback.format_exc()}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32000, "message": f"Internal error: {str(e)}"}
        }, status_code=500)

# 3) Lifespan
@asynccontextmanager
async def lifespan(app):
    logger.info("Iniciando lifespan de la aplicación ASGI")
    try:
        yield
    finally:
        logger.info("Finalizando lifespan de la aplicación ASGI")

# 4) CORS config (for MCP endpoint exposure)
allowed_origins = [os.getenv("ALLOWED_ORIGINS", "*")]
if allowed_origins == ["*"]:
    allow_origins = ["*"]
else:
    allow_origins = allowed_origins

logger.info(f"Configurando CORS con orígenes permitidos: {allow_origins}")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "Mcp-Session-Id"],
        allow_credentials=True,
    )
]

# 5) Root ASGI app combining MCP and Django
logger.info("Configurando aplicación ASGI principal con rutas MCP y Django")
application = Starlette(
    lifespan=lifespan,
    routes=[
        # MCP endpoint - handle both /mcp and /mcp/
        Route('/mcp', endpoint=mcp_endpoint, methods=['GET', 'POST']),
        Route('/mcp/', endpoint=mcp_endpoint, methods=['GET', 'POST']),
        # Django everything else
        Mount('/', app=django_asgi),
    ],
    middleware=middleware,
)
logger.info("Aplicación ASGI configurada correctamente")
