"""Thin async wrapper around the google-genai SDK for embeddings and chat."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from functools import lru_cache
from math import sqrt
from typing import TypeVar

from google import genai
from google.genai import types

from app.config import settings

log = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 100
EMBED_MAX_TRIES = 3
EMBED_BACKOFF_BASE_SECONDS = 1.0

T = TypeVar("T")


async def _with_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    tries: int = EMBED_MAX_TRIES,
    base_delay: float = EMBED_BACKOFF_BASE_SECONDS,
    label: str = "gemini call",
) -> T:
    """Run an awaitable factory up to `tries` times with exponential backoff."""
    for attempt in range(1, tries + 1):
        try:
            return await factory()
        except Exception as exc:
            if attempt == tries:
                log.error("%s failed after %d attempts: %s", label, tries, exc)
                raise
            delay = base_delay * (2 ** (attempt - 1))
            log.warning(
                "%s attempt %d/%d failed (%s); retrying in %.1fs",
                label, attempt, tries, exc, delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")


def _l2_normalize(vec: list[float]) -> list[float]:
    """Required when using non-default output_dimensionality (MRL truncation)."""
    norm = sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


async def embed_batch(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Embed many texts in batches of EMBED_BATCH_SIZE; preserves input order."""
    if not texts:
        return []

    client = _client()
    config = types.EmbedContentConfig(
        output_dimensionality=settings.embedding_dimensions,
        task_type=task_type,
    )

    out: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        response = await _with_retry(
            lambda b=batch: client.aio.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=b,
                config=config,
            ),
            label=f"embed_batch[{start}:{start + len(batch)}]",
        )
        for embedding in response.embeddings:
            out.append(_l2_normalize(list(embedding.values)))
    return out


async def chat(prompt: str | Iterable[str]) -> str:
    """One-shot non-streaming completion. Used by Phase 3."""
    client = _client()
    contents = prompt if isinstance(prompt, str) else list(prompt)
    response = await _with_retry(
        lambda: client.aio.models.generate_content(
            model=settings.gemini_chat_model,
            contents=contents,
        ),
        label="chat",
    )
    return response.text or ""


async def chat_stream(prompt: str | Iterable[str]) -> AsyncIterator[str]:
    """Yield text chunks from a Gemini completion as they arrive (Phase 4).

    The stream open is retried with backoff (transient 503s happen before any
    token is sent). Once tokens start flowing we don't retry mid-stream.
    """
    client = _client()
    contents = prompt if isinstance(prompt, str) else list(prompt)
    stream = await _with_retry(
        lambda: client.aio.models.generate_content_stream(
            model=settings.gemini_chat_model,
            contents=contents,
        ),
        label="chat_stream open",
    )
    async for chunk in stream:
        if chunk.text:
            yield chunk.text
