from __future__ import annotations
import os
import numpy as np
import sqlite3
from typing import List, Tuple
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

# Lazy import to avoid hard dependency until used
def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL) if OPENAI_BASE_URL else OpenAI(api_key=OPENAI_API_KEY)

def embed_texts(texts: List[str]) -> np.ndarray:
    client = _openai_client()
    resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=texts)
    vecs = [np.array(d.embedding, dtype=np.float32) for d in resp.data]
    return np.vstack(vecs)

def pack_vec(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()

def unpack_vec(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-12
    return float(np.dot(a, b) / denom)
