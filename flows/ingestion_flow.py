"""End-to-end FastAPI documentation ingestion flow."""

import os
import sys
# Ensure repository root is on sys.path so running the script directly works
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Disable telemetry to avoid amplitude shutdown noise during interpreter exit
os.environ.setdefault("DO_NOT_TRACK", "1")

from prefect import flow, task
from prefect.logging import get_run_logger

from src.config import settings
from src.ingestion.bm25_store import build_bm25_index
from src.ingestion.chunk import chunk_docs
from src.ingestion.embed import embed_texts
from src.ingestion.fetch import fetch_docs
from src.ingestion.vector_store import get_client, upsert_chunks


@task
def fetch_task():
    files = fetch_docs(settings.raw_data_dir, settings.github_token)
    get_run_logger().info("Fetched %d files", len(files))
    return files


@task
def chunk_task(_files):
    chunks = chunk_docs(settings.raw_data_dir)
    get_run_logger().info("Created %d chunks", len(chunks))
    return chunks


@task
def embed_task(chunks):
    return embed_texts([chunk["text"] for chunk in chunks])


@task
def index_task(chunks, embeddings):
    count = upsert_chunks(chunks, embeddings, get_client(settings.qdrant_url))
    get_run_logger().info("Indexed %d points into Qdrant", count)
    return count


@task
def bm25_task(chunks):
    build_bm25_index(chunks, settings.bm25_index_path)
    get_run_logger().info("Built BM25 index with %d documents", len(chunks))
    return len(chunks)


@flow
def ingest_fastapi_docs():
    files = fetch_task()
    chunks = chunk_task(files)
    embeddings = embed_task(chunks)
    index_task(chunks, embeddings)
    return bm25_task(chunks)


if __name__ == "__main__":
    ingest_fastapi_docs()