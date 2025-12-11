from __future__ import annotations
import os, argparse, sqlite3
#from dotenv import load_dotenv
#import django
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
#django.setup()
from civil.models import Causa
from civil.rag.sqlite_db import hybrid_search
from civil.rag.utils_embed import embed_texts
import logging
from typing import Dict, Any, List
import re

logger = logging.getLogger('mcp')

#load_dotenv()

def sanitize_fts_query(text: str) -> str:
    """
    Versión sencilla de saneo para FTS:
    - Reemplaza cualquier carácter raro (.,-/: etc.) por espacio
    - Deja solo letras, números y espacios.
    """
    if not text:
        return ""
    # Esto conserva letras, números y guiones bajos. El resto se vuelve espacio
    cleaned = re.sub(r"[^\wáéíóúüñÁÉÍÓÚÜÑ]+", " ", text)
    return cleaned.strip()

def embed_query(q: str):
    return embed_texts([q])[0]

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    demand_id = arguments.get("demand_id")
    query = arguments.get("question")
    k = arguments.get("k", 8)

    if not demand_id or not query:
        raise ValueError("Missing required arguments: demand_id and query")

    demand = Causa.objects.get(id=demand_id)

    print(f"Using demand: {demand.titulo} (id={demand.id}) sqlite_path={demand.sqlite_path}")
    if not demand.sqlite_path:
        raise SystemExit("Demand has no sqlite_path.")
    if not os.path.exists(demand.sqlite_path):
        raise SystemExit("SQLite path missing on disk.")

    with sqlite3.connect(demand.sqlite_path) as con:
        try:
            # Intento 1: usar pregunta original para FTS
            logger.info(f"[RAG] Ejecutando búsqueda híbrida con query original: {query!r}")
            embed_query_vector = embed_query(query)
            rows = hybrid_search(con, query, embed_query_vector, rerank_k=k)
        except sqlite3.OperationalError as e:
            logger.warning(
                f"[RAG] FTS error con query original: {e}. "
                f"Reintento con query saneada…"
            )
            safe_q = sanitize_fts_query(query)
            logger.info(f"[RAG] Query saneada: {safe_q!r}")
            rows = hybrid_search(con, safe_q, embed_query, rerank_k=k)
        for cid, content, score in rows:
            print(f"chunk_id={cid} score={score:.4f}\n{content[:300]}\n---")
    result = {
        "answer": None,
        "trace": None,
        "context_text": None,
        "results": [{"chunk_id": cid, "content": content, "score": score} for cid, content, score in rows],
        "db_path": demand.sqlite_path,
        "elapsed": None,
    }
    return result

