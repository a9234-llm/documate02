"""Prompt templates for RAG chain.
"""
from __future__ import annotations

from typing import List, Dict


def _format_context(chunks: List[Dict]) -> str:
    parts = []
    for c in chunks:
        src = c.get("source_file") or c.get("source") or ""
        heading = c.get("heading") or ""
        text = c.get("text") or c.get("payload", "")
        parts.append(f"Source: {src} | Heading: {heading}\n{text}\n---\n")
    return "\n".join(parts)


def baseline_prompt(question: str, chunks: List[Dict]) -> str:
    context = _format_context(chunks)
    return f"Answer the question using ONLY the context below. If the answer is not contained, say you don't know.\n\nContext:\n{context}\nQuestion: {question}\nAnswer:"


def expert_role_prompt(question: str, chunks: List[Dict]) -> str:
    context = _format_context(chunks)
    return (
        "You are an experienced Python/FastAPI developer. Answer concisely using ONLY the context below. "
        "If the answer cannot be found in the context, say you don't know. Provide a short code example if relevant.\n\n"
        f"Context:\n{context}\nQuestion: {question}\nAnswer:"
    )


def structured_prompt(question: str, chunks: List[Dict]) -> str:
    context = _format_context(chunks)
    return (
        "You are an assistant that replies with a structured answer. Return: 1) short answer, 2) example code block if applicable, 3) list of sources (file + heading). Use only the context below.\n\n"
        f"Context:\n{context}\nQuestion: {question}\nAnswer:"
    )


PROMPT_VARIANTS = {
    "baseline": baseline_prompt,
    "expert_role": expert_role_prompt,
    "structured": structured_prompt,
}


def get_prompt(variant: str, question: str, chunks: List[Dict]) -> str:
    fn = PROMPT_VARIANTS.get(variant)
    if fn is None:
        fn = expert_role_prompt
    return fn(question, chunks)
