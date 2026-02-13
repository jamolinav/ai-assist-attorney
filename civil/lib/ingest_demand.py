from __future__ import annotations
import os, re, json, math, argparse, sqlite3
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
from pypdf import PdfReader
from django.contrib.auth import get_user_model
from django.db import transaction
from civil.models import Causa
from civil.rag.sqlite_db import ensure_schema, insert_document, insert_chunk, insert_embedding
from civil.rag.utils_embed import embed_texts
import logging
from datetime import datetime

logger = logging.getLogger('civil')
User = get_user_model()

# naive chunking by characters (replace with token-based if needed)
def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    out = []
    i = 0
    n = len(text)
    while i < n:
        out.append(text[i:i + chunk_size])
        i += max(1, chunk_size - overlap)
    return [s.strip() for s in out if s.strip()]

def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n".join(pages)

def resolve_or_create_demand(
    demand_id: Optional[int],
    title: Optional[str],
    pdf_dir: Path,
    create_if_missing: bool,
    created_by_id: Optional[int],
) -> Causa:
    """
    Reglas:
    - Si viene demand_id: intenta get; si no existe y create_if_missing → crear con ese ID? (no, PK autoincrement).
        En ese caso creamos uno nuevo ignorando el id (informamos por pantalla).
    - Si no viene demand_id: intenta resolver por title; si no, por pdf_dir exacto.
    - Si no encuentra y create_if_missing → crear con title (o nombre del directorio como fallback).
    """
    creator = None
    if created_by_id:
        try:
            creator = User.objects.get(id=created_by_id)
        except User.DoesNotExist:
            logger.warning(f"--created-by={created_by_id} no existe; se continuará sin asignar.")

    # 1) demand_id
    if demand_id is not None:
        try:
            return Causa.objects.get(id=demand_id)
        except Causa.DoesNotExist:
            if not create_if_missing:
                logger.error(f"No se encontró la demanda con id={demand_id}. Use --create-if-missing para crearla.")
            # crear ignorando el id pedido
            actual_title = title or pdf_dir.name
            d = Causa.objects.create(
                title=actual_title,
                pdf_dir=str(pdf_dir),
                sqlite_path="",  # se llenará luego
                status="pending",
                created_by=creator,
            )
            logger.info(f"No se encontró la demanda con id={demand_id}. Se creó una nueva con id={d.id}.")
            return d

    # 2) sin demand_id: buscar por title, luego por pdf_dir
    if title:
        d = Causa.objects.filter(title=title).order_by("-created_at").first()
        if d:
            return d
    d = Causa.objects.filter(pdf_dir=str(pdf_dir)).order_by("-created_at").first()
    if d:
        return d

    # 3) crear si no se encontró
    if not create_if_missing:
        logger.error("No se encontró la demanda. Use --create-if-missing y/o entregue --title para crearla.")
        
    actual_title = title or pdf_dir.name
    d = Causa.objects.create(
        title=actual_title,
        pdf_dir=str(pdf_dir),
        sqlite_path="",
        status="pending",
        created_by=creator,
    )
    return d

def ingest_demand(self, *args, **options):
    demand_id = options.get("demand_id")
    title = options.get("title")
    pdf_dir = Path(options["pdf_dir"]).resolve()
    create_if_missing = options.get("create_if_missing", False)
    created_by_id = options.get("created_by")
    chunk_size = options.get("chunk_size")
    overlap = options.get("overlap")
    batch = options.get("batch")

    if not pdf_dir.exists():
        logger.error(f"El directorio {pdf_dir} no existe.")

    # Crear/Resolver la demanda
    demand = resolve_or_create_demand(demand_id, title, pdf_dir, create_if_missing, created_by_id)
    
    # Preparar el destino del SQLite
    download_dir = Path(os.getenv("SQLITE_LOCAL_PATH")) / datetime.now().strftime("%Y-%m-%d")
    download_dir.mkdir(parents=True, exist_ok=True)
    db_path = download_dir / f"demand_{demand.id}.db"

    files = sorted([p for p in pdf_dir.rglob("*.pdf")])
    if not files:
        logger.error(f"No se encontraron archivos PDF en {pdf_dir}.")

    logger.info(f"Ingestando demanda id={demand.id}, título='{demand.titulo}', {len(files)} PDFs desde {pdf_dir} → {db_path}")

    # Estado → processing
    with transaction.atomic():
        demand.status = "processing"
        demand.sqlite_path = os.path.join(datetime.now().strftime("%Y-%m-%d"), f"demand_{demand.id}.db")
        demand.pdf_dir = os.path.join(os.path.join(datetime.now().strftime("%Y-%m-%d"), f"demand_{demand.id}"))
        demand.save(update_fields=["status", "sqlite_path", "pdf_dir"])

    try:
        ensure_schema(str(db_path))
        total_chunks = 0
        with sqlite3.connect(str(db_path)) as con:
            for pdf in tqdm(files):
                logger.info(f"Procesando PDF: {pdf}")
                text = extract_pdf_text(str(pdf))
                chunks = chunk_text(text, chunk_size, overlap)
                if not chunks:
                    continue
                doc_id = insert_document(con, str(pdf), meta={"size": os.path.getsize(pdf)})
                # embeddings por lotes
                for i in range(0, len(chunks), batch):
                    batch_texts = chunks[i:i + batch]
                    vecs = embed_texts(batch_texts)
                    for j, (chunk_text_i, vec) in enumerate(zip(batch_texts, vecs)):
                        cid = insert_chunk(con, doc_id, chunk_text_i, seq=i + j)
                        insert_embedding(con, cid, vec)
                total_chunks += len(chunks)

        # Estado → ready y ruta sqlite
        with transaction.atomic():
            demand.status = "ready"
            demand.save(update_fields=["status"])

        logger.info(f"Ingesta completada: {total_chunks} chunks insertados en {db_path}")

    except Exception as e:
        with transaction.atomic():
            demand.status = "error"
            demand.save(update_fields=["status"])
        raise
