from __future__ import annotations

import os
from typing import List, Dict, Optional

from sentence_transformers import SentenceTransformer

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter
except Exception:  # pragma: no cover - optional dependency
    QdrantClient = None  # type: ignore


_MODEL: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _MODEL


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = _get_model()
    return model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()


def dense_search(query: str, top_k: int = 5, qdrant_url: Optional[str] = None, collection: str = "fastapi_docs") -> List[Dict]:
    """
    Search Qdrant by embedding of `query`.

    Returns list of chunks with keys: `id`, `score`, and payload fields if present.
    If Qdrant client is not available or env vars missing, raises RuntimeError with guidance.
    """
    if QdrantClient is None:
        raise RuntimeError("qdrant-client not installed or failed to import. Install qdrant-client to use dense_search.")

    url = qdrant_url or os.getenv("QDRANT_URL")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    if not url:
        raise RuntimeError("QDRANT_URL not set — cannot connect to Qdrant for dense search")

    client = QdrantClient(url=url, port=port)

    emb = _get_model().encode([query], convert_to_numpy=True)[0]

    hits = client.search(collection_name=collection, query_vector=emb.tolist(), limit=top_k)

    results = []
    for h in hits:
        payload = h.payload or {}
        results.append({
            "id": payload.get("id", str(h.id)),
            "score": float(h.score if hasattr(h, "score") else 0.0),
            **({k: v for k, v in payload.items()} if payload else {}),
        })
    return results
