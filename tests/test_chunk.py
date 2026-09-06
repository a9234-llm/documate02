from src.ingestion.chunk import chunk_markdown


def test_chunks_by_second_level_heading_and_filters_short_sections():
    markdown = "# Page\n\n## First\n\n" + "A useful section with enough content. " * 3
    markdown += "\n## Too short\n\nNo.\n"
    markdown += "\n## Second\n\n" + "Another useful section with enough content. " * 3
    chunks = chunk_markdown(markdown, "docs/en/docs/example.md")
    assert len(chunks) == 2
    assert chunks[0]["heading"] == "First"
    assert chunks[1]["heading"] == "Second"
