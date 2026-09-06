"""Markdown chunking by second-level headings."""

import re
from pathlib import Path
from typing import Any

from .fetch import source_url


def chunk_markdown(text: str, source_file: str, minimum_length: int = 50) -> list[dict[str, Any]]:
    """Split Markdown into `##` sections and discard very short sections."""
    matches = list(re.finditer(r"(?m)^##[ \t]+(.+?)\s*$", text))
    if not matches:
        sections = [("", text)]
    else:
        sections = [
            (
                match.group(1).strip(),
                text[match.start(): matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip(),
            )
            for i, match in enumerate(matches)
        ]
    return [
        {
            "id": f"{source_file}__{index}",
            "text": content,
            "source_file": source_file,
            "heading": heading,
            "url": source_url(source_file),
        }
        for index, (heading, content) in enumerate(sections)
        if len(content) >= minimum_length
    ]


def chunk_file(path: Path, root: Path) -> list[dict[str, Any]]:
    relative = path.relative_to(root).as_posix()
    return chunk_markdown(path.read_text(encoding="utf-8"), f"docs/en/docs/{relative}")


def chunk_docs(raw_dir: Path) -> list[dict[str, Any]]:
    return [chunk for path in sorted(raw_dir.rglob("*.md")) for chunk in chunk_file(path, raw_dir)]
