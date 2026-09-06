"""Simple RAG chain: retrieve context, build prompt, call LLM, return answer + sources."""
from __future__ import annotations

from typing import List, Dict, Callable
import logging

from src.llm.groq_client import default_client
from src.llm.prompts import get_prompt

from src.retrieval.dense import dense_search
from src.retrieval.bm25 import load_bm25_from_path
from src.retrieval.hybrid import hybrid_search
from src.config import settings

logger = logging.getLogger(__name__)


def _select_context_from_dense(dense_results: List[Dict], top_k: int) -> List[Dict]:
    out = []
    for d in dense_results[:top_k]:
        out.append({
            "id": d.get("id"),
            "text": d.get("text") or d.get("payload") or d.get("payload_text"),
            "source_file": d.get("source_file") or d.get("source") or d.get("source_file"),
            "heading": d.get("heading"),
            "url": d.get("url"),
        })
    return out


def answer_question(
    question: str,
    retriever: Callable | None = None,
    prompt_variant: str = "expert_role",
    top_k: int = 5,
) -> Dict:
    """Retrieve context and ask Groq for an answer.

    Returns: {"answer": str, "sources": List[Dict], "prompt": str}
    """
    # Try hybrid retriever if provided, but dense_search provides payloads for context
    try:
        dense_results = dense_search(question, top_k=top_k)
    except Exception as e:
        logger.warning("dense_search failed: %s", e)
        dense_results = []

    context_chunks = _select_context_from_dense(dense_results, top_k=top_k)

    # Build prompt
    prompt = get_prompt(prompt_variant, question, context_chunks)

    # Call LLM
    try:
        answer = default_client.generate(prompt=prompt)
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        answer = ""

    sources = [ {"id": c.get("id"), "source_file": c.get("source_file"), "heading": c.get("heading"), "url": c.get("url")} for c in context_chunks]

    return {"answer": answer, "sources": sources, "prompt": prompt}


if __name__ == "__main__":
    print("Example: call answer_question('What is dependency injection in FastAPI?')")
