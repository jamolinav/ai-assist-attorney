from __future__ import annotations
import os, re, json, math, argparse, sqlite3
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
from pypdf import PdfReader

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from portal.models import ProcessedDemand
from rag.sqlite_db import ensure_schema, insert_document, insert_chunk, insert_embedding
from rag.utils_embed import embed_texts

from pjud.celeryy import app

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

@app.task
def _resolve_or_create_demand(texts: List[str]) -> List[List[float]]:
    # "Crea/actualiza el SQLite por demanda a partir de PDFs y registra/actualiza Causa."
    '''
    parser.add_argument("--demand-id", type=int, required=False,
                        help="ID de ProcessedDemand existente (si no existe y --create-if-missing, se crea).")
    parser.add_argument("--title", type=str, required=False,
                        help="Título para crear o resolver la demanda si no se da --demand-id.")
    parser.add_argument("--pdf-dir", type=str, required=True,
                        help="Directorio con PDFs de la demanda.")
    parser.add_argument("--create-if-missing", action="store_true",
                        help="Si no se encuentra la demanda, crearla automáticamente.")
    parser.add_argument("--created-by", type=int, required=False,
                        help="ID de usuario (opcional) para asociar como creador si se crea la demanda.")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--batch", type=int, default=64)
    '''
    def _resolve_or_create_demand(
        self,
        demand_id: Optional[int],
        title: Optional[str],
        pdf_dir: Path,
        create_if_missing: bool,
        created_by_id: Optional[int],
    ) -> ProcessedDemand:
        """
        Reglas:
        - Si viene demand_id: intenta get; si no existe y create_if_missing → crear con ese ID? (no, PK autoincrement).
          En ese caso creamos uno nuevo ignorando el id (informamos por pantalla).
        - Si no viene demand_id: intenta resolver por title; si no, por pdf_dir exacto.
        - Si no encuentra y create_if_missing → crear con title (o nombre del directorio como fallback).
        """
    try:

        creator = None
        if created_by_id:
            try:
                creator = User.objects.get(id=created_by_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"--created-by={created_by_id} no existe; se continuará sin asignar."))

        # 1) demand_id
        if demand_id is not None:
            try:
                return ProcessedDemand.objects.get(id=demand_id)
            except ProcessedDemand.DoesNotExist:
                if not create_if_missing:
                    raise CommandError(f"ProcessedDemand id={demand_id} no existe (use --create-if-missing para crear).")
                # crear ignorando el id pedido
                actual_title = title or pdf_dir.name
                d = ProcessedDemand.objects.create(
                    title=actual_title,
                    pdf_dir=str(pdf_dir),
                    sqlite_path="",  # se llenará luego
                    status="pending",
                    created_by=creator,
                )
                self.stdout.write(self.style.WARNING(
                    f"Nota: id solicitado {demand_id} no existe; se creó nueva demanda con id={d.id}."
                ))
                return d

        # 2) sin demand_id: buscar por title, luego por pdf_dir
        if title:
            d = ProcessedDemand.objects.filter(title=title).order_by("-created_at").first()
            if d:
                return d
        d = ProcessedDemand.objects.filter(pdf_dir=str(pdf_dir)).order_by("-created_at").first()
        if d:
            return d

        # 3) crear si no se encontró
        if not create_if_missing:
            raise CommandError("No se encontró la demanda. Use --create-if-missing y/o entregue --title para crearla.")
        actual_title = title or pdf_dir.name
        d = ProcessedDemand.objects.create(
            title=actual_title,
            pdf_dir=str(pdf_dir),
            sqlite_path="",
            status="pending",
            created_by=creator,
        )
        return d

@app.task
def ingest_demand(options: dict):
    try:
        demand_id = options.get("demand_id")
        title = options.get("title")
        pdf_dir = Path(options["pdf_dir"]).resolve()
        create_if_missing = options.get("create_if_missing", False)
        created_by_id = options.get("created_by")
        chunk_size = options["chunk_size"]
        overlap = options["overlap"]
        batch = options["batch"]

        if not pdf_dir.exists():
            raise CommandError(f"pdf-dir not found: {pdf_dir}")

        # Crear/Resolver la demanda
        demand = self._resolve_or_create_demand(demand_id, title, pdf_dir, create_if_missing, created_by_id)

        # Preparar el destino del SQLite
        root = Path(os.getenv("DEMAND_SQLITE_ROOT", "./data/demands"))
        root.mkdir(parents=True, exist_ok=True)
        db_path = root / f"demand_{demand.id}.db"

        files = sorted([p for p in pdf_dir.rglob("*.pdf")])
        if not files:
            self.stdout.write(self.style.WARNING("No se encontraron PDFs en el directorio."))

        self.stdout.write(f"Ingestando {len(files)} PDFs en {db_path} (demanda id={demand.id}) ...")

        # Estado → processing
        with transaction.atomic():
            demand.status = "processing"
            demand.save(update_fields=["status"])

        try:
            ensure_schema(str(db_path))
            total_chunks = 0
            with sqlite3.connect(str(db_path)) as con:
                for pdf in tqdm(files):
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
                demand.sqlite_path = str(db_path)
                demand.status = "ready"
                demand.save(update_fields=["sqlite_path", "status"])

            self.stdout.write(self.style.SUCCESS(
                f"OK. Insertados ~{total_chunks} chunks. SQLite: {db_path}"
            ))

        except Exception as e:
            with transaction.atomic():
                demand.status = "error"
                demand.save(update_fields=["status"])
            raise
    except Exception as e:
        raise CommandError(f"Error durante la ingesta: {str(e)}")
