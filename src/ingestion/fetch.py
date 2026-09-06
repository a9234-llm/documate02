"""Fetch Markdown files from the FastAPI documentation repository."""

from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.github.com/repos/tiangolo/fastapi/contents/docs/en/docs"


def fetch_docs(output_dir: Path, token: str = "", timeout: int = 30) -> list[Path]:
    """Download all documentation Markdown files, preserving repository paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"******"
    downloaded: list[Path] = []

    def visit(url: str) -> None:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        entries: list[dict[str, Any]] = response.json()
        for entry in entries:
            if entry["type"] == "dir":
                visit(entry["url"])
            elif entry["type"] == "file" and entry["name"].endswith(".md"):
                relative = Path(entry["path"]).relative_to("docs/en/docs")
                destination = output_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                content = requests.get(entry["download_url"], headers=headers, timeout=timeout)
                content.raise_for_status()
                destination.write_text(content.text, encoding="utf-8")
                downloaded.append(destination)

    visit(API_URL)
    return downloaded


def source_url(source_file: str) -> str:
    """Return the public FastAPI documentation URL for a repository path."""
    path = source_file.removeprefix("docs/en/docs/").removesuffix(".md")
    if path.endswith("/index"):
        path = path.removesuffix("/index")
    elif path == "index":
        path = ""
    return f"https://fastapi.tiangolo.com/{path}/"
