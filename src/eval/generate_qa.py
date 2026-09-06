from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import List, Dict

try:
    import groq
except Exception:
    groq = None  # optional


def _read_md_files(root: str) -> List[Path]:
    p = Path(root)
    files = list(p.rglob("*.md"))
    return files


def _extract_text(p: Path) -> str:
    text = p.read_text(encoding="utf8")
    # remove code blocks for brevity
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    # collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


def _heuristic_question_from_text(text: str) -> str:
    # take first meaningful sentence and craft a question
    sentences = re.split(r"(?<=[\.\?!])\s+", text)
    for s in sentences:
        s = s.strip()
        if len(s) > 40:
            # turn into a What/How question
            if s.lower().startswith("how") or s.lower().startswith("what"):
                return s if s.endswith("?") else s + "?"
            return f"What is meant by: {s[:80].rstrip()}?"
    # fallback
    return "What is the main idea of this documentation fragment?"


def generate_eval_dataset(data_root: str = "data/raw", out_path: str = "data/eval_qa.jsonl", sample_n: int = 100) -> None:
    files = _read_md_files(data_root)
    if not files:
        raise RuntimeError(f"No markdown files found under {data_root}")

    chosen = random.sample(files, min(sample_n, len(files)))
    out = []
    use_groq = groq is not None and os.getenv("GROQ_API_KEY")

    for fp in chosen:
        txt = _extract_text(fp)
        if not txt:
            continue
        snippet = txt[:2000]
        if use_groq:
            try:
                client = groq.Groq()
                prompt = f"Ты помогаешь создать тестовый датасет для системы вопрос-ответ по документации FastAPI. На основе следующего фрагмента документации сгенерируй ОДИН конкретный вопрос, ответ на который содержится в этом фрагменте. Верни только вопрос, без преамбулы. Фрагмент: {snippet}"
                resp = client.generate(prompt=prompt)
                question = resp["text"].strip()
            except Exception:
                question = _heuristic_question_from_text(snippet)
        else:
            question = _heuristic_question_from_text(snippet)

        out.append({"chunk_id": fp.as_posix(), "question": question, "source_file": fp.as_posix()})

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf8") as f:
        for obj in out:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    generate_eval_dataset()
