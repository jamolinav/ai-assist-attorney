"""
Tools package - Funciones principales para el manejo de herramientas MCP
"""

from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP

import importlib
import inspect
import anyio
import logging

# Configurar logger
logger = logging.getLogger('mcp')


# Importar el gestor desde el directorio padre
import sys
from pathlib import Path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from mcp_app.tools_manager import ToolsManager

# Instancia global del gestor de herramientas
tools_manager = ToolsManager()


def get_tools_list() -> List[Dict[str, Any]]:
    """Carga la lista de herramientas desde tools_list.json"""
    return tools_manager.get_available_tools()

async def call_tool_async(name: str, arguments: dict):
    """
    Versión ASÍNCRONA segura para usar en vistas async.
    - Si la tool es async → await.
    - Si es sync → se ejecuta en thread pool.
    """
    mod = importlib.import_module(f"mcp_app.tools.{name}")
    fn = getattr(mod, "execute")
    if inspect.iscoroutinefunction(fn):
        return await fn(arguments)
    else:
        return await anyio.to_thread.run_sync(fn, arguments)

def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta una herramienta usando el gestor de herramientas."""
    return tools_manager.execute_tool(tool_name, arguments)


def register_tools(mcp: FastMCP) -> None:
    """Registra dinámicamente las herramientas basadas en tools_list.json."""
    tools_list = get_tools_list()
    
    # Validar la estructura de herramientas
    errors = tools_manager.validate_tool_structure()
    if errors:
        print("Errores encontrados en la validación de herramientas:")
        for error in errors:
            print(f"  - {error}")
    
    for tool_config in tools_list:
        tool_name = tool_config["name"]
        tool_description = tool_config["description"]
        
        # Cargar el módulo usando el gestor
        tool_module = tools_manager.load_tool_module(tool_name)
        if tool_module is None:
            continue
        
        try:
            # Crear wrapper para registro con FastMCP
            def create_tool_wrapper(name):
                def tool_wrapper(**kwargs) -> Dict[str, Any]:
                    try:
                        result = tools_manager.execute_tool(name, kwargs)
                        # Extraer el contenido del resultado MCP para compatibilidad con FastMCP
                        if isinstance(result, dict) and "content" in result:
                            content = result["content"][0]["text"] if result["content"] else "No content"
                            return {"ok": True, "result": content}
                        return {"ok": True, "result": str(result)}
                    except Exception as e:
                        return {"ok": False, "error": str(e)}
                return tool_wrapper
            
            # Registrar la herramienta con FastMCP
            wrapper = create_tool_wrapper(tool_name)
            wrapper.__name__ = tool_name
            wrapper.__doc__ = tool_description
            
            # Registrar usando el decorador de FastMCP
            mcp.tool()(wrapper)
            print(f"Herramienta '{tool_name}' registrada exitosamente")
            
        except Exception as e:
            print(f"Error registrando herramienta '{tool_name}': {e}")


# Exponer las funciones principales
__all__ = ['get_tools_list', 'call_tool', 'register_tools', 'tools_manager', 'call_tool_async']
