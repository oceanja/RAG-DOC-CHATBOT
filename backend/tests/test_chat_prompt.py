"""Pure-function tests for the RAG prompt builder.

These don't hit Gemini or the DB — they just verify that retrieved chunks
are stitched into the prompt in the right shape, citations included, and
the 'I don't know' instruction survives.
"""

import uuid

from app.services.chat import _build_prompt
from app.services.retrieval import RetrievedChunk


def _chunk(content: str, title: str = "Doc", url: str | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        title=title,
        source_url=url,
        content=content,
        distance=0.1,
    )


def test_prompt_includes_question_and_project_name():
    prompt = _build_prompt("ReactKit", "What is JSX?", [_chunk("JSX is...")])
    assert "ReactKit" in prompt
    assert "What is JSX?" in prompt


def test_prompt_numbers_citations_starting_at_one():
    chunks = [_chunk("first chunk"), _chunk("second chunk"), _chunk("third chunk")]
    prompt = _build_prompt("Demo", "any?", chunks)
    assert "[1] first chunk" in prompt
    assert "[2] second chunk" in prompt
    assert "[3] third chunk" in prompt
    assert "[4]" not in prompt


def test_prompt_includes_grounding_instructions():
    prompt = _build_prompt("Demo", "x?", [_chunk("y")])
    assert "ONLY the context" in prompt
    assert "I don't know" in prompt


def test_prompt_handles_empty_retrieval():
    prompt = _build_prompt("Demo", "anything?", [])
    assert "no context found" in prompt
    assert "anything?" in prompt
