"""Semantic similarity via sentence-transformers (all-MiniLM-L6-v2).

The model is loaded lazily as a process-wide singleton. If the library or model
weights are unavailable (e.g. offline CI), the service degrades to a
token-overlap (Jaccard) similarity so the pipeline still produces sensible
scores rather than crashing.
"""
from __future__ import annotations

import threading
from functools import lru_cache

from ..config import settings

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _model = SentenceTransformer(settings.EMBEDDING_MODEL)
                except Exception:
                    _model = False  # sentinel: unavailable
    return _model


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def similarity(a: str, b: str) -> float:
    """Cosine similarity in [0, 1] between two texts."""
    if not a or not b:
        return 0.0
    model = _get_model()
    if not model:
        return _jaccard(a, b)
    import numpy as np
    emb = model.encode([a, b], normalize_embeddings=True)
    cos = float(np.dot(emb[0], emb[1]))
    return max(0.0, min(1.0, (cos + 1) / 2 if cos < 0 else cos))


def max_pairwise_similarity(query: str, candidates: list[str]) -> float:
    """Best match of `query` against a list of candidate strings."""
    if not query or not candidates:
        return 0.0
    model = _get_model()
    if not model:
        return max((_jaccard(query, c) for c in candidates), default=0.0)
    import numpy as np
    vecs = model.encode([query] + candidates, normalize_embeddings=True)
    q, rest = vecs[0], vecs[1:]
    sims = rest @ q
    return float(max(0.0, min(1.0, sims.max())))


@lru_cache(maxsize=2048)
def _cached_embed(text: str):
    model = _get_model()
    if not model:
        return None
    return tuple(model.encode(text, normalize_embeddings=True).tolist())


def skill_set_coverage(required: list[str], candidate: list[str], threshold: float = 0.62):
    """Return (matched, missing) for required skills vs candidate skills using
    semantic matching, so 'cybersecurity' can satisfy 'information security'.
    """
    matched, missing = [], []
    cand_lower = [c.lower() for c in candidate]
    for req in required:
        r = req.lower()
        if r in cand_lower:
            matched.append(req)
            continue
        best = max_pairwise_similarity(r, cand_lower) if cand_lower else 0.0
        (matched if best >= threshold else missing).append(req)
    return matched, missing
