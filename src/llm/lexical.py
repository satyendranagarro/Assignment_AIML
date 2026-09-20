"""Offline lexical hash embeddings for local smoke tests (no API key)."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from langchain_core.embeddings import Embeddings

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def _bin_index(token: str, size: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % size


class LexicalHashEmbeddings(Embeddings):
    """Bag-of-hashed-tokens vectors so overlapping terms retrieve nearby chunks."""

    def __init__(self, size: int = 384) -> None:
        if size < 16:
            raise ValueError("size must be >= 16")
        self.size = size

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.size
        toks = _tokens(text)
        if not toks:
            return vec
        for tok in toks:
            idx = _bin_index(tok, self.size)
            vec[idx] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]
