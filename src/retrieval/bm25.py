from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Optional

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> List[str]:
    # simple tokenization: lowercase + split on non-alphanumeric
    return [t for t in re.split(r"[^0-9a-zA-Z]+", text.lower()) if t]


class BM25Store:
    def __init__(self, docs: Optional[List[Dict]] = None):
        self.docs = docs or []
        self.doc_ids: List[str] = []
        self.tokenized: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def build(self, docs: List[Dict]):
        self.docs = docs
        self.doc_ids = [d["id"] for d in docs]
        self.tokenized = [_tokenize(d.get("text", "")) for d in docs]
        self.bm25 = BM25Okapi(self.tokenized)

    def save(self, path: str):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "doc_ids": self.doc_ids,
            "docs": [{"id": d["id"], "text": d.get("text", ""), "meta": {k: d.get(k) for k in ("source_file", "heading", "url")}} for d in self.docs],
            "tokenized": self.tokenized,
        }
        # BM25Okapi is not pickle-friendly here; we just store docs + tokens and rebuild on load
        p.write_text(json.dumps(payload, ensure_ascii=False))

    def load(self, path: str):
        p = Path(path)
        data = json.loads(p.read_text())
        self.doc_ids = data["doc_ids"]
        self.docs = [{"id": d["id"], "text": d.get("text", ""), **(d.get("meta", {}))} for d in data["docs"]]
        self.tokenized = data["tokenized"]
        self.bm25 = BM25Okapi(self.tokenized)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if self.bm25 is None:
            raise RuntimeError("BM25 index not built or loaded")
        q_tokens = _tokenize(query)
        scores = self.bm25.get_scores(q_tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for idx, score in ranked:
            doc = self.docs[idx]
            results.append({"id": doc["id"], "score": float(score), "text": doc.get("text", ""), "source_file": doc.get("source_file"), "heading": doc.get("heading"), "url": doc.get("url")})
        return results


def load_bm25_from_path(path: str) -> BM25Store:
    store = BM25Store()
    store.load(path)
    return store
