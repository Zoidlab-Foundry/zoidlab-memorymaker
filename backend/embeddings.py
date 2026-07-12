"""Local semantic embeddings — fastembed (BAAI/bge-small-en-v1.5, 384-dim, ONNX/CPU).

Recall uses a small local embedding model (the Nyquest relay has no embeddings endpoint).
Lazy-loaded and fail-soft: if fastembed isn't installed or the model can't load,
`available()` is False and the recall engine falls back to keyword scoring.
"""
import os
import math

MODEL_NAME = os.environ.get("MM_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
ENABLED = os.environ.get("ENABLE_REAL_EMBEDDINGS", "true").lower() != "false"
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None
_load_failed = False


def _get():
    global _model, _load_failed
    if _model is not None or _load_failed or not ENABLED:
        return _model
    try:
        from fastembed import TextEmbedding
        _model = TextEmbedding(MODEL_NAME)
    except Exception as e:
        import sys
        print(f"[memorymaker] embeddings unavailable ({str(e)[:120]}); using keyword recall.", file=sys.stderr)
        _load_failed = True
        _model = None
    return _model


def available():
    return _get() is not None


def embed_texts(texts):
    m = _get()
    if not m:
        return None
    return [list(map(float, v)) for v in m.embed(list(texts))]


def embed_query(text):
    m = _get()
    if not m:
        return None
    v = next(iter(m.embed([_QUERY_PREFIX + (text or "")])), None)
    return list(map(float, v)) if v is not None else None


def cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
