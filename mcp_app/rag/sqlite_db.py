from __future__ import annotations
import os, sqlite3, json, numpy as np
from typing import List, Tuple, Iterable, Optional
from .utils_embed import pack_vec, unpack_vec, embed_texts, cosine_sim

SCHEMA_SQL = '''
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    meta_json TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    seq INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    vector BLOB NOT NULL
);

-- FTS5 for BM25 retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, chunk_id UNINDEXED, tokenize='porter');
-- contentless option could be used; here we keep content
'''

def ensure_schema(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.executescript(SCHEMA_SQL)

def insert_document(con: sqlite3.Connection, path: str, meta: dict | None=None) -> int:
    cur = con.execute("INSERT INTO documents(path, meta_json) VALUES(?, ?)", (path, json.dumps(meta or {}, ensure_ascii=False)))
    return int(cur.lastrowid)

def insert_chunk(con: sqlite3.Connection, document_id: int, content: str, seq: int) -> int:
    cur = con.execute("INSERT INTO chunks(document_id, content, seq) VALUES(?,?,?)", (document_id, content, seq))
    chunk_id = int(cur.lastrowid)
    con.execute("INSERT INTO chunks_fts(rowid, content, chunk_id) VALUES(?,?,?)", (chunk_id, content, chunk_id))
    return chunk_id

def insert_embedding(con: sqlite3.Connection, chunk_id: int, vector):
    con.execute("INSERT INTO embeddings(chunk_id, vector) VALUES(?, ?)", (chunk_id, pack_vec(vector)))

def topk_bm25(con: sqlite3.Connection, query: str, k: int=40) -> List[Tuple[int, str]]:
    sql = "SELECT rowid, content FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?"
    return [(int(r[0]), r[1]) for r in con.execute(sql, (query, k)).fetchall()]

def fetch_embeddings(con: sqlite3.Connection, chunk_ids: Iterable[int]) -> List[tuple]:
    qmarks = ",".join("?" for _ in chunk_ids)
    sql = f"SELECT c.id, c.content, e.vector FROM chunks c JOIN embeddings e ON e.chunk_id=c.id WHERE c.id IN ({qmarks})"
    return con.execute(sql, tuple(chunk_ids)).fetchall()

def hybrid_search(con: sqlite3.Connection, query: str, embed_query, bm25_k=40, rerank_k=8):
    # Step 1: lexical
    candidates = topk_bm25(con, query, k=bm25_k)
    if not candidates:
        return []
    ids = [cid for cid, _ in candidates]
    rows = fetch_embeddings(con, ids)
    # Step 2: embedding rerank
    qvec = embed_query(query)
    scored = []
    for cid, content, blob in rows:
        vec = unpack_vec(blob)
        scored.append((cid, content, cosine_sim(qvec, vec)))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:rerank_k]
