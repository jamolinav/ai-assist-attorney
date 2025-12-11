import logging
import traceback
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from .tools_manager import ToolsManager
import importlib
import inspect
import anyio

# Configurar logger
logger = logging.getLogger('mcp')

# Instancia global del gestor de herramientas
logger.info("Inicializando gestor de herramientas")
tools_manager = ToolsManager()

def call_tool(name: str, arguments: dict):
    """
    Versión síncrona existente (si ya la tienes, déjala tal cual para contextos sync).
    Solo asegúrate de que NO se use desde handlers async.
    """
    mod = importlib.import_module(f"mcp_app.tools.{name}")
    fn = getattr(mod, "execute")
    if inspect.iscoroutinefunction(fn):
        # No podemos await aquí (somos sync) → ejecuta un loop temporal:
        return anyio.run(fn, arguments)  # ⚠️ No usar desde vistas async
    else:
        return fn(arguments)

def get_tools_list() -> List[Dict[str, Any]]:
    """Carga la lista de herramientas desde tools_list.json"""
    logger.debug("Obteniendo lista de herramientas disponibles")
    try:
        print("Getting tools list...")
        tools = tools_manager.get_available_tools()
        print(f"Loaded {len(tools)} tools from {tools_manager.tools_list_file}")
        logger.info(f"Lista de herramientas obtenida exitosamente: {len(tools)} herramientas")
        return tools
    except Exception as e:
        logger.error(f"Error obteniendo lista de herramientas: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return []

def register_tools(mcp: FastMCP) -> None:
    """Registra dinámicamente las herramientas basadas en tools_list.json."""
    logger.info("Iniciando registro de herramientas MCP")
    
    try:
        logger.debug("Cargando lista de herramientas desde tools_list.json")
        tools_list = get_tools_list()
        logger.info(f"Obtenidas {len(tools_list)} herramientas para registrar")
        
        # Validar la estructura de herramientas
        logger.debug("Validando estructura de herramientas")
        errors = tools_manager.validate_tool_structure()
        if errors:
            logger.warning("Errores encontrados en la validación de herramientas:")
            for error in errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("Estructura de herramientas validada correctamente")
    
        for tool_config in tools_list:
            tool_name = tool_config["name"]
            tool_description = tool_config["description"]
            
            logger.debug(f"Procesando herramienta: {tool_name}")
            logger.debug(f"Descripción: {tool_description}")
            
            # Cargar el módulo usando el gestor
            tool_module = tools_manager.load_tool_module(tool_name)
            if tool_module is None:
                logger.warning(f"No se pudo cargar el módulo para la herramienta: {tool_name}")
                continue
        
            try:
                logger.debug(f"Creando wrapper para herramienta: {tool_name}")
                
                # Crear wrapper para registro con FastMCP
                def create_tool_wrapper(name):
                    def tool_wrapper(**kwargs) -> Dict[str, Any]:
                        logger.debug(f"Ejecutando wrapper de herramienta: {name}")
                        try:
                            result = tools_manager.execute_tool(name, kwargs)
                            # Extraer el contenido del resultado MCP para compatibilidad con FastMCP
                            if isinstance(result, dict) and "content" in result:
                                content = result["content"][0]["text"] if result["content"] else "No content"
                                logger.debug(f"Wrapper {name} - resultado extraído: {content}")
                                return {"ok": True, "result": content}
                            logger.debug(f"Wrapper {name} - resultado directo: {result}")
                            return {"ok": True, "result": str(result)}
                        except Exception as e:
                            logger.error(f"Error en wrapper de herramienta {name}: {str(e)}")
                            logger.error(f"Traceback:\n{traceback.format_exc()}")
                            return {"ok": False, "error": str(e)}
                    return tool_wrapper
                
                # Registrar la herramienta con FastMCP
                wrapper = create_tool_wrapper(tool_name)
                wrapper.__name__ = tool_name
                wrapper.__doc__ = tool_description
                
                # Registrar usando el decorador de FastMCP
                mcp.tool()(wrapper)
                logger.info(f"Herramienta '{tool_name}' registrada exitosamente")
                
            except Exception as e:
                logger.error(f"Error registrando herramienta '{tool_name}': {str(e)}")
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                
    except Exception as e:
        logger.critical(f"Error crítico durante el registro de herramientas: {str(e)}")
        logger.critical(f"Traceback completo:\n{traceback.format_exc()}")
        raise