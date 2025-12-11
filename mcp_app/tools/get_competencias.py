from civil.models import Competencia
import logging
from typing import Dict, Any, List

logger = logging.getLogger('mcp')

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.info("Iniciando la función get_competencias.")

        query = Competencia.objects.all()
        # Campos a devolver
        fields: List[str] = arguments.get("fields") or ["id", "nombre"]
        valid_fields = {f.name for f in Competencia._meta.get_fields()}
        selected_fields = [f for f in fields if f in valid_fields] or ["id", "nombre"]

        results = list(query.values(*selected_fields))
        logger.info("Consulta de competencias finalizada.")
        return {"status": "success", "data": results, "count": len(results)}

    except Exception as e:
        logger.error(f"Error en get_competencias: {e}")
        return {"status": "error", "message": str(e)}
