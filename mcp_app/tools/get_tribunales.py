from civil.models import Tribunal
import logging
from typing import Dict, Any, List

logger = logging.getLogger('mcp')

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.info("Iniciando la función get_tribunales.")

    
        # Filtro obligatorio
        if "corte" in arguments:
            query = Tribunal.objects.filter(corte_id=arguments["corte"])
        else:
            raise ValueError("El parámetro 'corte' es obligatorio.")

        # Orden y paginación
        order_by = arguments.get("order_by", "nombre")
        limit = int(arguments.get("limit", 100))
        offset = int(arguments.get("offset", 0))
        query = query.order_by(order_by)[offset:offset + limit]

        # Campos a devolver
        fields: List[str] = arguments.get("fields") or ["id", "nombre", "jurisdiccion", "tipo_causa"]
        valid_fields = {f.name for f in Tribunal._meta.get_fields()}
        selected_fields = [f for f in fields if f in valid_fields] or ["id", "nombre"]

        results = list(query.values(*selected_fields))
        logger.info("Consulta de tribunales finalizada.")
        return {"status": "success", "data": results, "count": len(results)}

    except Exception as e:
        logger.error(f"Error en get_tribunales: {e}")
        return {"status": "error", "message": str(e)}
