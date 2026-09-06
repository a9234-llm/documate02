"""Qdrant storage for document chunks."""

from typing import Any, Iterable

from qdrant_client import QdrantClient, models

COLLECTION_NAME = "fastapi_docs"
VECTOR_SIZE = 384


def get_client(url: str = "http://localhost:6333") -> QdrantClient:
    return QdrantClient(url=url)


def upsert_chunks(
    chunks: Iterable[dict[str, Any]],
    embeddings: Iterable[list[float]],
    client: QdrantClient | None = None,
) -> int:
    client = client or QdrantClient(":memory:")
    chunk_list, vector_list = list(chunks), list(embeddings)
    if len(chunk_list) != len(vector_list):
        raise ValueError("chunks and embeddings must have the same length")

    # Recreats collection from the scratch each run which guarantees the absence
    # of the "junk" points in the subsequent runs with another number of chunks
    client.recreate_collection(
        COLLECTION_NAME,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )

    client.upsert(
        COLLECTION_NAME,
        points=[
            models.PointStruct(id=index, vector=vector, payload=chunk)
            for index, (chunk, vector) in enumerate(zip(chunk_list, vector_list))
        ],
    )
    return len(chunk_list)