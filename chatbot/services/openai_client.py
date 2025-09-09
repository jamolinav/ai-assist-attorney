from typing import Dict

# from openai import OpenAI # Descomentar cuando se integre
# import os
def generate_answer(prompt: str, user_context: Dict) -> str:
    """Función mock para generar respuesta.
    # TODO: Reemplazar por llamada real a OpenAI.
    """
    # client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    # ...
    return (
        "Esta es una respuesta simulada del abogado virtual. "
        "En producción, se integrará con OpenAI y con tus fuentes de datos."
    )

# - Leer OPENAI_API_KEY desde variables de entorno.
# - Enviar contexto del usuario (respetando privacidad/consentimiento).
# - Calcular usage (tokens) y costos.
# - Manejar errores/transientes/timeouts.
"""
# client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# ...
return (
"Esta es una respuesta simulada del abogado virtual. "
"En producción, se integrará con OpenAI y con tus fuentes de datos."
)
"""