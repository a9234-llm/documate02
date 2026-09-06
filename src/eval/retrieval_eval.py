from __future__ import annotations

import json
from typing import Callable, Dict, List


def hit_rate_at_k(retrieved: List[Dict], ground_truth_id: str, k: int) -> int:
    for i, r in enumerate(retrieved[:k]):
        if r.get("id") == ground_truth_id:
            return 1
    return 0


def reciprocal_rank(retrieved: List[Dict], ground_truth_id: str, k: int) -> float:
    for i, r in enumerate(retrieved[:k]):
        if r.get("id") == ground_truth_id:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_retriever(retriever_fn: Callable[[str, int], List[Dict]], eval_data: List[Dict], k: int = 5) -> Dict:
    """
    eval_data: list of {"chunk_id": <ground truth id>, "question": <str>}
    retriever_fn: function(question, top_k) -> list of {'id': ...}
    returns dict with hit_rate and mrr
    """
    hits = 0
    rr_sum = 0.0
    n = 0
    for item in eval_data:
        q = item["question"]
        gt = item["chunk_id"]
        retrieved = retriever_fn(q, top_k=k)
        hits += hit_rate_at_k(retrieved, gt, k)
        rr_sum += reciprocal_rank(retrieved, gt, k)
        n += 1

    if n == 0:
        return {"hit_rate": 0.0, "mrr": 0.0, "n": 0}

    return {"hit_rate": hits / n, "mrr": rr_sum / n, "n": n}


def load_eval_file(path: str) -> List[Dict]:
    out = []
    with open(path, "r", encoding="utf8") as f:
        for line in f:
            if not line.strip():
                continue
            out.append(json.loads(line))
    return out


if __name__ == "__main__":
    import sys
    print("Usage: import evaluate_retriever and call it with your retriever function")
