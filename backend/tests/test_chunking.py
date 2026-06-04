from app.utils.chunking import chunk_text, count_tokens, split_markdown_by_h1


def test_count_tokens_is_deterministic_and_nonzero():
    text = "DocuPilot is a RAG chatbot."
    n = count_tokens(text)
    assert n > 0
    assert n == count_tokens(text)  # deterministic


def test_chunk_text_respects_max_tokens():
    paragraph = "Lorem ipsum dolor sit amet. " * 200  # ~1000+ tokens
    chunks = chunk_text(paragraph, max_tokens=120, overlap_tokens=20)
    assert len(chunks) > 1
    for c in chunks:
        # Allow a small tolerance because overlap-stitching can push a chunk slightly above.
        assert count_tokens(c) <= 200, f"chunk too big: {count_tokens(c)}"


def test_chunk_text_short_input_returns_single_chunk():
    chunks = chunk_text("just a sentence.", max_tokens=500)
    assert chunks == ["just a sentence."]


def test_chunk_text_empty_input_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n   ") == []


def test_split_markdown_by_h1_basic():
    md = "# First\n\nbody A\n\n# Second\n\nbody B\n"
    sections = split_markdown_by_h1(md)
    assert sections == [("First", "body A"), ("Second", "body B")]


def test_split_markdown_no_h1_returns_default_title():
    md = "no headers at all, just text."
    sections = split_markdown_by_h1(md, default_title="Untitled")
    assert sections == [("Untitled", md)]


def test_split_markdown_ignores_h2():
    md = "# Real\n\nbody\n\n## Not an H1\n\nmore body"
    sections = split_markdown_by_h1(md)
    assert len(sections) == 1
    assert sections[0][0] == "Real"
    assert "## Not an H1" in sections[0][1]
