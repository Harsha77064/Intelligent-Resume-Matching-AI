"""Semantic similarity between a job description and a resume.

Uses Sentence Transformers (all-MiniLM-L6-v2) when installed; otherwise falls
back to a fast, dependency-free TF-IDF cosine similarity. Embeddings are cached
by text hash so re-running matching does not re-encode unchanged resumes.

Engine selection via the SEMANTIC_ENGINE env var: "auto" (default), "embeddings", "tfidf".
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import threading
from collections import Counter

log = logging.getLogger(__name__)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_ENGINE_PREF = os.getenv("SEMANTIC_ENGINE", "auto").lower()

_model = None
_model_lock = threading.Lock()
_model_failed = False
_cache: dict[str, list[float]] = {}
_CACHE_MAX = 5000

STOPWORDS = set(
    """a an and are as at be been but by can for from has have he her his i in into is it its
    of on or our she that the their them they this to was we were will with you your who what
    which while within work worked working years year experience using used use also etc via per
    role team teams responsible responsibilities strong good ability skills skill knowledge""".split()
)
TOKEN_RE = re.compile(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]")


def load_model():
    global _model, _model_failed
    if _model is not None or _model_failed or _ENGINE_PREF == "tfidf":
        return _model
    with _model_lock:
        if _model is not None or _model_failed:
            return _model
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME)
            log.info("Semantic engine: sentence-transformers (%s)", MODEL_NAME)
        except Exception as exc:  # not installed / no network / unsupported python
            _model_failed = True
            if _ENGINE_PREF == "embeddings":
                log.error("Embeddings requested but unavailable: %s", exc)
            else:
                log.info("Sentence Transformers unavailable (%s); using TF-IDF fallback", exc.__class__.__name__)
    return _model


def warm_up() -> None:
    """Load the embedding model in a background thread at startup."""
    threading.Thread(target=load_model, daemon=True).start()


def engine_name() -> str:
    if _model is not None:
        return f"embeddings ({MODEL_NAME.split('/')[-1]})"
    if _ENGINE_PREF != "tfidf" and not _model_failed:
        return "tfidf (embedding model loading)"
    return "tfidf"


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


def _embed(texts: list[str]) -> list[list[float]]:
    model = _model
    missing = [t for t in texts if _key(t) not in _cache]
    if missing:
        vecs = model.encode([t[:4000] for t in missing], normalize_embeddings=True, batch_size=32,
                            show_progress_bar=False)
        if len(_cache) > _CACHE_MAX:
            _cache.clear()
        for t, v in zip(missing, vecs):
            _cache[_key(t)] = [float(x) for x in v]
    return [_cache[_key(t)] for t in texts]


def _tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def _tfidf_scores(query: str, docs: list[str]) -> list[float]:
    corpus = [_tokens(query)] + [_tokens(d) for d in docs]
    n = len(corpus)
    df: Counter = Counter()
    for toks in corpus:
        df.update(set(toks))
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def vec(toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    q = vec(corpus[0])
    out = []
    for toks in corpus[1:]:
        d = vec(toks)
        out.append(sum(w * d.get(t, 0.0) for t, w in q.items()))
    return out


def similarity_batch(job_text: str, resume_texts: list[str]) -> tuple[list[float], str]:
    """Return calibrated 0..1 similarity for each resume, plus engine name used."""
    if not resume_texts:
        return [], engine_name()
    if _model is not None:
        try:
            vecs = _embed([job_text] + resume_texts)
            q = vecs[0]
            raw = [sum(a * b for a, b in zip(q, v)) for v in vecs[1:]]
            # MiniLM cosine: unrelated job/resume pairs ~0.15-0.3, strong fits ~0.7-0.8
            return [min(1.0, max(0.0, (r - 0.25) / 0.5)) for r in raw], engine_name()
        except Exception as exc:  # pragma: no cover
            log.warning("Embedding failed, falling back to TF-IDF: %s", exc)
    raw = _tfidf_scores(job_text, resume_texts)
    # TF-IDF cosine between a JD and a resume rarely exceeds ~0.4
    return [min(1.0, r / 0.35) for r in raw], "tfidf"
