import importlib
import json
import os

def load_tools_config(config_path='mcp_app/tools_config.json'):
    with open(config_path, 'r') as f:
        config = json.load(f)

    tools = {}
    for tool_name, tool_info in config['tools'].items():
        module_path = tool_info['module']
        method_name = tool_info['method']
        module = importlib.import_module(module_path)
        method = getattr(module, method_name)
        tools[tool_name] = method

    return tools
