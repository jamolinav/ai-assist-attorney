import json
from django.apps import apps
from django.db.models import Model

class MCPProcessor:
    def __init__(self, function_definitions_path='mcp/function_descriptions.json'):
        with open(function_definitions_path, 'r') as f:
            self.function_definitions = {func['name']: func for func in json.load(f)}
    
    def list_functions(self):
        return list(self.function_definitions.keys())

    def run(self, operation, parameters):
        if operation not in self.function_definitions:
            raise ValueError(f"Operación '{operation}' no encontrada.")

        if operation.startswith("get_"):
            model_name = operation.replace("get_", "").capitalize()
            model_class = self.get_model_class(model_name)
            return self.run_query(model_class, parameters.get('filters', {}))

        raise NotImplementedError(f"La operación '{operation}' no está implementada.")

    def get_model_class(self, model_name):
        for model in apps.get_models():
            if model.__name__.lower() == model_name.lower():
                return model
        raise ValueError(f"Modelo '{model_name}' no encontrado.")

    def run_query(self, model_class, filters):
        if not issubclass(model_class, Model):
            raise ValueError("Clase inválida para consulta ORM.")
        query = model_class.objects.filter(**filters)
        results = list(query.values())
        return results

    def execute_chain(self, steps):
        """
        Ejecuta una cadena de pasos de operaciones para resolver multi-transacciones.
        Cada step debe tener: operation, parameters
        """
        context = {}
        for step in steps:
            operation = step['operation']
            parameters = step.get('parameters', {})
            result = self.run(operation, parameters)
            context[operation] = result
        return context
