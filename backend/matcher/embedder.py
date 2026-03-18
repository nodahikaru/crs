"""Compute text embeddings using OpenAI API with joblib disk cache."""

import hashlib

import httpx
import joblib
import numpy as np
from openai import OpenAI

from config import settings

# Module-level disk cache — persists across requests and server restarts
_memory = joblib.Memory(location=".cache/embeddings", verbose=0)


@_memory.cache
def _fetch_embeddings_cached(texts_key: str, texts: list[str], model: str) -> list[list[float]]:
    """Fetch embeddings from OpenAI. Cached on disk by (texts_key, model).

    texts_key is a SHA-256 hash of the sorted texts + model, used as the
    joblib cache key. texts is passed separately so joblib can store the
    actual payload.
    """
    http_client = httpx.Client(proxy=None)
    client = OpenAI(api_key=settings.OPENAI_API_KEY, http_client=http_client)

    results: list[list[float]] = [None] * len(texts)  # type: ignore[list-item]

    for i in range(0, len(texts), 2000):
        chunk = texts[i : i + 2000]
        response = client.embeddings.create(model=model, input=chunk)
        for offset, data in enumerate(response.data):
            results[i + offset] = data.embedding

    return results


def _cache_key(texts: list[str], model: str) -> str:
    """Stable SHA-256 key for a list of texts + model."""
    payload = model + "\n" + "\n---\n".join(texts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Embedder:
    def __init__(self, model: str | None = None):
        self.model = model or settings.EMBEDDING_MODEL
        # In-memory cache for the current request (avoids repeated disk reads)
        self._cache: dict[str, list[float]] = {}

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts. Returns (N, dim) numpy array.

        Cache hierarchy:
          1. In-memory dict  — free, lives for this request
          2. joblib disk     — fast, survives restarts
          3. OpenAI API      — slow, billed
        """
        if not texts:
            return np.array([])

        uncached = [t for t in texts if t not in self._cache]

        if uncached:
            key = _cache_key(uncached, self.model)
            embeddings = _fetch_embeddings_cached(key, uncached, self.model)
            for text, embedding in zip(uncached, embeddings):
                self._cache[text] = embedding

        return np.array([self._cache[t] for t in texts])