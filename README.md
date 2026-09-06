# DocuMate02

Simple ingestion pipeline for a FastAPI documentation RAG assistant.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d qdrant postgres
python flows/ingestion_flow.py
python scripts/sanity_check.py
```

The pipeline downloads Markdown documentation from FastAPI's GitHub repository,
splits it at `##` headings, creates 384-dimensional local embeddings, and
stores both dense (Qdrant) and lexical (BM25) indexes.