"""Small persistent BM25 index."""

import pickle
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def build_bm25_index(chunks: list[dict[str, Any]], path: Path) -> BM25Okapi:
    index = BM25Okapi([tokenize(chunk["text"]) for chunk in chunks])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        pickle.dump({"index": index, "chunk_ids": [chunk["id"] for chunk in chunks]}, output)
    return index


def load_bm25_index(path: Path) -> dict[str, Any]:
    with path.open("rb") as source:
        return pickle.load(source)
