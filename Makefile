PY := python3
PIP := pip3

.PHONY: help install gen-eval run-eval test sample-search

help:
	@echo "Makefile targets:"
	@echo "  install       - install python deps from requirements.txt"
	@echo "  gen-eval      - generate synthetic eval dataset (data/eval_qa.jsonl)"
	@echo "  run-eval      - run retrieval evaluation and write docs/retrieval_evaluation_results.md"
	@echo "  test          - run pytest"
	@echo "  sample-search - run a sample BM25 search against data/raw files"

install:
	$(PIP) install -r requirements.txt

gen-eval:
	$(PY) -c "from src.eval.generate_qa import generate_eval_dataset; generate_eval_dataset()"

run-eval:
	$(PY) scripts/run_retrieval_eval.py

test:
	pytest -q

sample-search:
	$(PY) - <<'PY'
from src.retrieval.bm25 import BM25Store
from src.eval.generate_qa import _read_md_files, _extract_text
files=_read_md_files('data/raw')
docs=[]
for fp in files[:50]:
    txt=_extract_text(fp)
    if txt:
        docs.append({'id':fp.as_posix(),'text':txt,'source_file':fp.as_posix(),'heading':''})
store=BM25Store(); store.build(docs)
print('Built BM25 on', len(docs),'docs')
for q in ['dependency injection','BackgroundTasks','upload file','security']:
    print('\nQuery:',q)
    for r in store.search(q,top_k=5):
        print('-',r['id'],f"score={r['score']:.2f}")
PY
