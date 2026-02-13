# =========================
# MCP tool interface
# =========================
import os, sqlite3, textwrap, re, logging, time, json, uuid
from typing import Dict, Any, List
import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
django.setup()
from civil.models import Causa
from civil.rag.sqlite_db import hybrid_search
from civil.rag.utils_embed import embed_texts
from openai import OpenAI
import datetime as dt
import logging

logger = logging.getLogger("mcp")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
logger = logging.getLogger("mcp_app.tools.rag_query")

SYSTEM_PROMPT = """Eres un abogado analista de textos judiciales.\nSi el contexto es suficiente, responde con:\nFINAL_ANSWER: <tu respuesta concluyente y breve>\n\nSi NO es suficiente, responde SOLO con:\nNEED_MORE_CONTEXT: <hasta 3 consultas o palabras clave concretas separadas por punto y coma>\n\nCuando debas pedir más contexto, en NEED_MORE_CONTEXT usa solo palabras clave limpias (sin puntos, guiones ni signos), en minúsculas, sin fechas ni RUTs.\nEjemplos válidos: \"pagare; ley 20027; banco internacional\"\nEjemplos inválidos: \"97.011.000-3; Ley 20.027; EN LO PRINCIPAL:\"\n"""
FTS_SAFE_CHARS = r"0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ"

def _client():
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL) if OPENAI_BASE_URL else OpenAI(api_key=OPENAI_API_KEY)

def embed_query(q: str):
    return embed_texts([q])[0]

def fts_sanitize(q: str) -> str:
    q2 = re.sub(fr"[^{FTS_SAFE_CHARS}]+", " ", q or "")
    q2 = " ".join(q2.split())
    return q2

def fts_prefixify(q: str) -> str:
    toks = q.split()
    return " ".join(f"{t}*" for t in toks)

def _more_context(con, demand_id: int, query_text: str, k: int = 4) -> str:
    t0 = time.perf_counter()
    q_orig = (query_text or "").strip()
    q_safe = fts_sanitize(q_orig)
    logger.debug("[CTX] more_context original_q='%s' safe_q='%s'", q_orig, q_safe)
    if not q_safe:
        logger.debug("[CTX] Consulta vacía tras sanitizar; no agrego contexto.")
        return ""
    try:
        rows = hybrid_search(con, q_safe, embed_texts, rerank_k=k)
        logger.debug("[CTX] hybrid_search rows=%d (q_safe='%s')", len(rows or []), q_safe)
    except sqlite3.OperationalError as e:
        logger.warning("[CTX] FTS error con q_safe='%s': %s. Intento fallback con prefijo.", q_safe, e)
        q_safe2 = fts_prefixify(q_safe)
        try:
            rows = hybrid_search(con, q_safe2, embed_texts, rerank_k=k)
            logger.debug("[CTX] hybrid_search (fallback) rows=%d (q_safe2='%s')", len(rows or []), q_safe2)
        except sqlite3.OperationalError as e2:
            logger.error("[CTX] FTS fallo incluso con fallback q_safe2='%s': %s", q_safe2, e2)
            return ""
    if not rows:
        logger.debug("[CTX] Sin filas de contexto para q='%s'", q_safe)
        return ""
    parts = []
    for idx, r in enumerate(rows):
        try:
            cid, content, score = r
        except Exception:
            cid, content = r[0], r[1]
            score = -1.0
        snippet = (content or "")[:1200]
        parts.append(f"[chunk:{cid} score={score:.3f}]\n{snippet}")
        if idx < 5:
            logger.debug("[CTX] +chunk id=%s score=%.3f len=%d", cid, score, len(snippet))
    ctx = "\n---\n".join(parts)
    t1 = time.perf_counter()
    logger.info("[CTX] Contexto agregado (%d chunks, %.1f KB) en %.3fs", len(parts), len(ctx)/1024.0, t1 - t0)
    return ctx

def _chat_until_conclusive(client, messages, con, demand_id: int, max_rounds: int = 3):
    logger.info("[LLM] Inicio loop con max_rounds=%d, modelo=%s", max_rounds, OPENAI_CHAT_MODEL)
    for round_idx in range(1, max_rounds + 1):
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=messages,
                temperature=0.2,
            )
        except Exception as e:
            logger.exception("[LLM] Error llamando al modelo en ronda %d: %s", round_idx, e)
            return f"Error al consultar el modelo: {e}"
        dt = time.perf_counter() - t0
        choice = resp.choices[0]
        txt = (choice.message.content or "").strip()
        logger.info("[LLM] Ronda %d completada en %.3fs. Respuesta_len=%d", round_idx, dt, len(txt))
        logger.debug("[LLM] Respuesta ronda %d (primeras 200): %r", round_idx, txt[:200])
        if txt.startswith("FINAL_ANSWER:"):
            answer = txt.removeprefix("FINAL_ANSWER:").strip()
            logger.info("[LLM] Conclusivo en ronda %d. answer_len=%d", round_idx, len(answer))
            return answer
        if txt.startswith("NEED_MORE_CONTEXT:"):
            raw_queries = txt.split(":", 1)[1] if ":" in txt else ""
            queries = [q.strip() for q in raw_queries.split(";") if q.strip()]
            logger.info("[LLM] Pide más contexto en ronda %d. queries=%s", round_idx, queries)
            extra_ctx_parts = []
            for q in queries:
                ctx_piece = _more_context(con, demand_id, q, k=4)
                if ctx_piece:
                    extra_ctx_parts.append(ctx_piece)
            extra_ctx = "\n\n".join(extra_ctx_parts).strip()
            if not extra_ctx:
                logger.warning("[LLM] No se pudo obtener contexto adicional (queries=%s). Detengo.", queries)
                break
            logger.info("[LLM] Agrego contexto adicional len=%.1f KB", len(extra_ctx)/1024.0)
            messages.append({"role": "system", "content": f"Contexto adicional:\n{extra_ctx}"})
            continue
        logger.warning("[LLM] Respuesta fuera de formato esperado. Devuelvo literal.")
        return txt
    logger.warning("[LLM] Agotadas rondas sin respuesta concluyente.")
    return "No fue posible obtener una respuesta concluyente con el contexto disponible."

def _write_trace(trace: dict, out_dir: str = "traces") -> str:
    os.makedirs(out_dir, exist_ok=True)
    fname = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
    fpath = os.path.join(out_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)
    logger.info("[TRACE] guardado en %s", fpath)
    return fpath

def safe_hybrid_search(con, raw_query: str, embed_fn, bm25_k=40, rerank_k=8):
    try:
        return hybrid_search(con, raw_query, embed_fn, bm25_k=bm25_k, rerank_k=rerank_k)
    except sqlite3.OperationalError as e1:
        logger.warning("[RAG] FTS error con query original: %s. Reintento con saneado…", e1)
        q_safe = fts_sanitize(raw_query)
        if not q_safe:
            return []
        try:
            return hybrid_search(con, q_safe, embed_fn, bm25_k=bm25_k, rerank_k=rerank_k)
        except sqlite3.OperationalError as e2:
            logger.warning("[RAG] FTS error con q_safe='%s': %s. Reintento con prefijo…", q_safe, e2)
            q_pref = fts_prefixify(q_safe)
            try:
                return hybrid_search(con, q_pref, embed_fn, bm25_k=bm25_k, rerank_k=rerank_k)
            except sqlite3.OperationalError as e3:
                logger.error("[RAG] FTS fallo incluso con prefijo q_pref='%s': %s", q_pref, e3)
                return []

def rag_answer(demand_id: int, question: str, k: int = 8):
    t_start = time.perf_counter()
    logger.info("[RAG] demand_id=%s question=%r model=%s base_url=%s", demand_id, question, OPENAI_CHAT_MODEL, OPENAI_BASE_URL or "(default)")
    try:
        demand = Causa.objects.filter(id=demand_id).first()
        if not demand:
            return f"Demanda procesada con id={demand_id} no existe.", None, None, None, None, None
    except Causa.DoesNotExist:
        msg = f"Demanda procesada con id={demand_id} no existe."
        logger.error("[RAG] %s", msg)
        raise RuntimeError(msg)
    
    WEBSITE_SITE_NAME = os.environ.get('WEBSITE_SITE_NAME', '')
    SQLITE_PATH = os.getenv("SQLITE_PATH")

    if 'azurewebsites.net' in WEBSITE_SITE_NAME:
        db_path = f'{SQLITE_PATH}{demand.sqlite_path}'
    else:
        SQLITE_LOCAL_PATH = os.getenv("SQLITE_LOCAL_PATH")
        db_path = f'{SQLITE_LOCAL_PATH}{demand.sqlite_path}'

    logger.info("[RAG] Ruta SQLite determinada: %s", db_path)
    
    
    if not db_path or not os.path.exists(db_path):
        msg = "SQLite de la demanda no existe o no está registrado."
        logger.error("[RAG] %s path=%r", msg, db_path)
        raise RuntimeError(msg)
    logger.info("[RAG] SQLite path=%s size=%.1f MB", db_path, (os.path.getsize(db_path) / (1024*1024.0)))
    seed_q = fts_prefixify(fts_sanitize(question or ""))
    seed_ctx = ""
    try:
        with sqlite3.connect(db_path) as con:
            if seed_q:
                seed_ctx = _more_context(con, demand_id, seed_q, k=4)
    except Exception as e:
        logger.exception("[RAG] Error generando seed context: %s", e)
    t0 = time.perf_counter()
    with sqlite3.connect(db_path) as con:
        results = safe_hybrid_search(con, question, embed_query, bm25_k=40, rerank_k=k)
    dtm = time.perf_counter() - t0
    logger.info("[RAG] hybrid_search inicial -> %d resultados en %.3fs (k=%d)", len(results), dtm, k)
    context_blocks = []
    for idx, row in enumerate(results):
        try:
            cid, content, score = row
        except Exception:
            cid, content = row[0], row[1]
            score = -1.0
        snippet = (content or "")[:800]
        context_blocks.append(f"[chunk:{cid} score={score:.3f}]\n{snippet}")
        if idx < 10:
            logger.debug("[RAG] top%d: cid=%s score=%.3f snippet_len=%d", idx+1, cid, score, len(snippet))
    context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "(sin resultados)"
    if seed_ctx:
        context_text = f"{context_text}\n\n---\n\n[seed]\n{seed_ctx}"
    logger.info("[RAG] context_len=%.1f KB", len(context_text)/1024.0)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Pregunta: {question}\n\ncontext:\n{context_text}"},
    ]
    client = _client()
    try:
        with sqlite3.connect(db_path) as con:
            answer = _chat_until_conclusive(client, messages, con, demand_id, max_rounds=3)
    except Exception as e:
        logger.exception("[RAG] Error en loop LLM: %s", e)
        answer = f"Error en loop LLM: {e}"
    logger.info("[RAG] Fin rag_answer en %.3fs", time.perf_counter() - t_start)
    trace = {
        "demand_id": demand_id,
        "question": question,
        "model": OPENAI_CHAT_MODEL,
        "db_path": db_path,
        "context_len": len(context_text),
        "top_chunks": [
            {"chunk_id": int(r[0]), "score": (float(r[2]) if len(r) > 2 else None)}
            for r in results[:8]
        ],
        "answer": answer,
        "ts": dt.datetime.now().isoformat(),
    }
    try:
        _write_trace(trace)
    except Exception as e:
        logger.warning("[TRACE] no se pudo escribir: %s", e)
    elapsed = time.perf_counter() - t_start
    return answer, trace, context_text, results, db_path, elapsed

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool entrypoint for RAG query. Receives arguments dict and returns JSON result.
    arguments: dict with keys: demand_id (int), question (str), conversation_id (str, optional), log_level (str, optional), k (int, optional)
    """
    demand_id = arguments.get("demand_id")
    question = arguments.get("question")
    conversation_id = arguments.get("conversation_id") or str(uuid.uuid4())

    print(f"RAG execute called with demand_id={demand_id} question={question!r} conversation_id={conversation_id}")
    
    k = arguments.get("k", 8)
    t0 = time.perf_counter()
    try:
        answer, trace, context_text, results, db_path, elapsed_inner = rag_answer(demand_id, question, k=k)
    except Exception as e:
        logger.exception("Error fatal en rag_answer: %s", e)
        answer = f"Error: {e}"
        trace = {}
        context_text = ""
        results = []
        db_path = None
        elapsed_inner = None
    elapsed = time.perf_counter() - t0
    result = {
        "conversation_id": conversation_id,
        "answer": answer.strip() if isinstance(answer, str) else answer,
        "elapsed_seconds": round(elapsed, 3),
        "trace": trace,
        "context_len": len(context_text) if context_text else 0,
        "db_path": db_path,
        "top_chunks": trace.get("top_chunks") if trace else [],
        "model": trace.get("model") if trace else OPENAI_CHAT_MODEL,
    }
    logger.info("RAG execute finalizado result=%s", {k: v for k, v in result.items() if k != "answer"})
    return result