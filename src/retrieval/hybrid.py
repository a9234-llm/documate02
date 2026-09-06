from __future__ import annotations

from typing import Callable, Dict, List


def _to_rank_map(results: List[Dict]) -> Dict[str, int]:
    # map id -> 1-based rank
    return {r["id"]: i + 1 for i, r in enumerate(results)}


def rrf_merge(ranked_lists: List[List[Dict]], k: int = 60) -> List[Dict]:
    """
    Reciprocal Rank Fusion (RRF).
    `ranked_lists` is a list of ranked result lists (each element is dict with 'id' and optionally 'score').
    Returns merged list of dicts with 'id' and 'score' (RRF score), sorted descending.
    """
    score_map = {}
    for rl in ranked_lists:
        rank_map = _to_rank_map(rl)
        for doc_id, rank in rank_map.items():
            score_map[doc_id] = score_map.get(doc_id, 0.0) + 1.0 / (k + rank)

    merged = [{"id": did, "score": sc} for did, sc in score_map.items()]
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged


def hybrid_search(query: str, top_k: int = 5, dense_fn: Callable = None, bm25_fn: Callable = None, rrf_k: int = 60) -> List[Dict]:
    """
    Hybrid search using RRF over dense and bm25. `dense_fn` and `bm25_fn` should accept (query, top_k) and return list of dicts with 'id'.
    If a retriever function is None, it's skipped.
    """
    ranked = []
    if dense_fn is not None:
        try:
            dres = dense_fn(query, top_k=top_k * 4)
        except Exception:
            dres = []
        ranked.append(dres)
    if bm25_fn is not None:
        bres = bm25_fn(query, top_k=top_k * 4)
        ranked.append(bres)

    if not ranked:
        return []

    merged = rrf_merge(ranked, k=rrf_k)
    return merged[:top_k]
