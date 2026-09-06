"""Application settings loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    raw_data_dir: Path = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    bm25_index_path: Path = Path(os.getenv("BM25_INDEX_PATH", "data/bm25_index.pkl"))


settings = Settings()
