"""LLM evaluation harness: compare prompt variants using Groq as judge when available.
"""
from __future__ import annotations

import json
from typing import List, Dict
from statistics import mean

from src.llm.rag_chain import answer_question
from src.llm.groq_client import default_client, GroqClient
from src.llm.prompts import PROMPT_VARIANTS
from src.eval.retrieval_eval import load_eval_file


def _judge_with_groq(question: str, context: str, answer: str) -> Dict:
    client = default_client
    try:
        prompt = (
            "Оцени ответ по шкале 1-5 по критериям: релевантность, точность, полнота. "
            f"Вопрос: {question}\nКонтекст: {context}\nОтвет: {answer}\nВерни JSON вида: {{\"relevance\": X, \"accuracy\": X, \"completeness\": X}}"
        )
        raw = client.generate(prompt=prompt)
        # try to extract json
        if raw.strip().startswith("{"):
            return json.loads(raw)
    except Exception:
        pass
    # fallback neutral scores
    return {"relevance": 3, "accuracy": 3, "completeness": 3}


def evaluate_prompt_variants(eval_file: str = "data/eval_qa.jsonl", sample_n: int = 30) -> Dict[str, Dict[str, float]]:
    data = load_eval_file(eval_file)
    if not data:
        raise RuntimeError("No eval data found; run src/eval/generate_qa.py first")

    sample = data[:sample_n]
    results = {}

    for variant in PROMPT_VARIANTS.keys():
        scores = {"relevance": [], "accuracy": [], "completeness": []}
        for item in sample:
            q = item["question"]
            # get context via rag chain (it will retrieve and include short context)
            out = answer_question(q, prompt_variant=variant, top_k=3)
            ans = out["answer"]
            # join context pieces for judge prompt
            context_str = "\n".join([s.get("source_file", "") + " - " + (s.get("heading") or "") for s in out.get("sources", [])])
            score = _judge_with_groq(q, context_str, ans)
            for k in scores.keys():
                scores[k].append(float(score.get(k, 3)))

        results[variant] = {k: mean(v) if v else 0.0 for k, v in scores.items()}

    return results


if __name__ == "__main__":
    import sys
    out = evaluate_prompt_variants()
    print(json.dumps(out, indent=2, ensure_ascii=False))
