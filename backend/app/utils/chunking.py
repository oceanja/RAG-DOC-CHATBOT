"""Recursive text chunking with tiktoken-based size measurement.

Tries separators from coarse (paragraph) to fine (word) until each piece
fits the target token budget. Adds a small token overlap between adjacent
chunks so cross-boundary context survives.
"""

from functools import lru_cache

import tiktoken

from app.config import settings

DEFAULT_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")


@lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text))


def _split_with_separator(text: str, separator: str) -> list[str]:
    if separator == "":
        return list(text)
    parts = text.split(separator)
    # Re-attach the separator to keep boundaries readable in chunks.
    return [p + separator for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _recursive_split(text: str, max_tokens: int, separators: tuple[str, ...]) -> list[str]:
    if count_tokens(text) <= max_tokens:
        return [text] if text.strip() else []

    separator, *rest = separators if separators else ("",)
    pieces = _split_with_separator(text, separator)

    result: list[str] = []
    for piece in pieces:
        if count_tokens(piece) <= max_tokens:
            result.append(piece)
        else:
            result.extend(_recursive_split(piece, max_tokens, tuple(rest)))
    return result


def _merge_pieces(pieces: list[str], max_tokens: int, overlap_tokens: int) -> list[str]:
    """Greedily merge small pieces up to max_tokens, then advance with overlap."""
    enc = _encoder()
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0

    for piece in pieces:
        piece_tokens = count_tokens(piece)
        if buffer and buffer_tokens + piece_tokens > max_tokens:
            chunk_text = "".join(buffer).strip()
            if chunk_text:
                chunks.append(chunk_text)
            # Seed the next buffer with the tail of the previous one for overlap.
            if overlap_tokens > 0 and chunks:
                tail_ids = enc.encode(chunks[-1])[-overlap_tokens:]
                tail = enc.decode(tail_ids)
                buffer = [tail]
                buffer_tokens = len(tail_ids)
            else:
                buffer = []
                buffer_tokens = 0
        buffer.append(piece)
        buffer_tokens += piece_tokens

    if buffer:
        chunk_text = "".join(buffer).strip()
        if chunk_text:
            chunks.append(chunk_text)
    return chunks


def chunk_text(
    text: str,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks bounded by max_tokens."""
    max_tokens = max_tokens or settings.chunk_size_tokens
    overlap_tokens = overlap_tokens if overlap_tokens is not None else settings.chunk_overlap_tokens

    text = text.strip()
    if not text:
        return []

    pieces = _recursive_split(text, max_tokens, DEFAULT_SEPARATORS)
    return _merge_pieces(pieces, max_tokens, overlap_tokens)


def split_markdown_by_h1(raw_md: str, default_title: str = "Untitled") -> list[tuple[str, str]]:
    """Split a markdown document into (title, body) sections at H1 boundaries.

    If no H1 is present, the whole document is returned as one section.
    Content before the first H1 (if any) is dropped.
    """
    lines = raw_md.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, current_body))
            current_title = line[2:].strip() or default_title
            current_body = []
        else:
            current_body.append(line)

    if current_title is not None:
        sections.append((current_title, current_body))

    if not sections:
        body = raw_md.strip()
        return [(default_title, body)] if body else []

    return [(title, "\n".join(body).strip()) for title, body in sections if "\n".join(body).strip()]
