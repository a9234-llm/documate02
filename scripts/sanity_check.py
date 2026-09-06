"""Print a few dense-search results after ingestion."""

import os
import sys
# Ensure repository root is on sys.path so running the script directly works
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Disable telemetry to avoid amplitude shutdown noise during interpreter exit
os.environ.setdefault("DO_NOT_TRACK", "1")

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
