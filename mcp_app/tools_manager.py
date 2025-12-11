"""
Utilidades para la gestión dinámica de herramientas MCP.
"""

import os
import json
import importlib
from pathlib import Path
from typing import Dict, Any, List
import logging
import traceback

logger = logging.getLogger("mcp")

class ToolsManager:
    """Gestor de herramientas que carga dinámicamente los módulos."""
    
    def __init__(self, tools_dir: str = None, tools_list_file: str = None):
        """
        Inicializa el gestor de herramientas.
        
        Args:
            tools_dir: Directorio donde están los módulos de herramientas
            tools_list_file: Archivo JSON con las definiciones de herramientas
        """
        current_dir = Path(__file__).parent
        self.tools_dir = Path(tools_dir) if tools_dir else current_dir / "tools"
        self.tools_list_file = Path(tools_list_file) if tools_list_file else current_dir / "tools_list.json"
        self._tools_cache = {}
        self.tools_loaded = {}
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de herramientas disponibles desde el archivo JSON."""
        try:
            logger.info(f"Loading tools list from {self.tools_list_file}")
            with open(self.tools_list_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Error: No se encontró el archivo {self.tools_list_file}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def load_tool_module(self, tool_name: str):
        """
        Carga dinámicamente un módulo de herramienta.
        
        Args:
            tool_name: Nombre de la herramienta
            
        Returns:
            Módulo cargado o None si hay error
        """
        if tool_name in self._tools_cache:
            return self._tools_cache[tool_name]
        
        try:
            module_path = f"mcp_app.tools.{tool_name}"
            logger.info(f"Cargando módulo de herramienta: {module_path}")
            tool_module = importlib.import_module(module_path)
            
            if not hasattr(tool_module, 'execute'):
                raise ValueError(f"El módulo {module_path} no tiene una función 'execute'")
            
            self._tools_cache[tool_name] = tool_module
            return tool_module
            
        except ImportError as e:
            logger.error(f"Error: No se pudo cargar la herramienta '{tool_name}': {e}")
            logger.error(traceback.format_exc())
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una herramienta específica.
        
        Args:
            tool_name: Nombre de la herramienta
            arguments: Argumentos para la herramienta
            
        Returns:
            Resultado de la ejecución en formato MCP
        """
        tool_module = self.load_tool_module(tool_name)
        
        if tool_module is None:
            raise ValueError(f"No se pudo cargar la herramienta '{tool_name}'")
        
        try:
            return tool_module.execute(arguments)
        except Exception as e:
            logger.error(f"Error ejecutando la herramienta '{tool_name}': {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Error ejecutando la herramienta '{tool_name}': {e}")
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Obtiene la información de configuración de una herramienta específica.
        
        Args:
            tool_name: Nombre de la herramienta
            
        Returns:
            Diccionario con la configuración de la herramienta o None si no existe
        """
        tools = self.get_available_tools()
        for tool in tools:
            if tool.get("name") == tool_name:
                return tool
        return None
    
    def validate_tool_structure(self) -> List[str]:
        """
        Valida que todos los módulos de herramientas existan y tengan la estructura correcta.
        
        Returns:
            Lista de errores encontrados
        """
        errors = []
        tools = self.get_available_tools()
        
        for tool in tools:
            tool_name = tool.get("name")
            if not tool_name:
                errors.append("Herramienta sin nombre encontrada en tools_list.json")
                continue
            
            # Verificar que el módulo existe y se puede cargar
            tool_module = self.load_tool_module(tool_name)
            if tool_module is None:
                errors.append(f"No se pudo cargar el módulo para '{tool_name}'")
                continue
            
            # Verificar que tiene función execute
            if not hasattr(tool_module, 'execute'):
                errors.append(f"El módulo '{tool_name}' no tiene función 'execute'")
        
            '''
            module = importlib.import_module(module_path)
            method = getattr(module, method_name)
            tools[tool_name] = method
            '''
            method = getattr(tool_module, 'execute', None)
            self.tools_loaded[tool_name] = method
            logger.info(f"Herramienta '{tool_name}' cargada exitosamente.")

        if not errors:
            logger.info("Todas las herramientas están correctamente configuradas.")
        else:
            logger.error("Errores encontrados en la configuración de herramientas:")
            for err in errors:
                logger.error(f"- {err}")
        return errors
