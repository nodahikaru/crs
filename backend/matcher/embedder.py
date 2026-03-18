"""Compute text embeddings using OpenAI API with in-memory caching."""

import httpx
import numpy as np
from openai import OpenAI

from config import settings


class Embedder:
    def __init__(self, model: str | None = None):
        http_client = httpx.Client(proxy=None)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY, http_client=http_client)
        self.model = model or settings.EMBEDDING_MODEL
        self._cache: dict[str, list[float]] = {}

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts. Returns (N, dim) numpy array.

        Uses in-memory cache to avoid redundant API calls.
        Batches API calls in chunks of 2000 (API limit is 2048).
        """
        if not texts:
            return np.array([])

        # Find uncached texts
        uncached = [t for t in texts if t not in self._cache]

        if uncached:
            for i in range(0, len(uncached), 2000):
                chunk = uncached[i:i + 2000]
                response = self.client.embeddings.create(
                    model=self.model,
                    input=chunk,
                )
                for text, data in zip(chunk, response.data):
                    self._cache[text] = data.embedding

        return np.array([self._cache[t] for t in texts])
