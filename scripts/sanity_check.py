"""Print a few dense-search results after ingestion."""

from src.config import settings
from src.ingestion.embed import embed_texts
from src.ingestion.vector_store import COLLECTION_NAME, get_client


def main() -> None:
    client = get_client(settings.qdrant_url)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embed_texts(["How do I use dependency injection?"])[0],
        limit=5,
    ).points
    for result in results:
        print(result.score, result.payload.get("source_file"), result.payload.get("heading"))


if __name__ == "__main__":
    main()
