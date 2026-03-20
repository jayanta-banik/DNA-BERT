from __future__ import annotations

from collections import OrderedDict
from hashlib import blake2b
from typing import Literal

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_METHOD: Literal["fuzzy", "semantic"] = "fuzzy"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_LIMIT = None
SEMANTIC_BATCH_SIZE = 256
SEMANTIC_CACHE_SIZE = 4

_EMBEDDING_CACHE: OrderedDict[tuple[str, str], np.ndarray] = OrderedDict()
_MODEL_CACHE: dict[str, object] = {}


class RankTexts:
    def __init__(
        self,
        values: list[str] | pd.Series,
        query: str,
        method: Literal["fuzzy", "semantic"] = DEFAULT_METHOD,
        limit: int | None = DEFAULT_LIMIT,
        threshold: float | None = None,
        *,
        model_name: str = DEFAULT_MODEL_NAME,
    ):
        """Rank text values against a query using fuzzy or semantic similarity."""
        normalized_values = _normalize_values(values)
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query must be a non-empty string")
        if method not in {"fuzzy", "semantic"}:
            raise ValueError("method must be one of {'fuzzy', 'semantic'}")
        if limit is not None and limit <= 0:
            raise ValueError("limit must be a positive integer or None")

        self.query = normalized_query
        self.method = method
        self.limit = limit
        self.threshold = threshold
        self.model_name = model_name
        self.source_values = normalized_values

        if normalized_values.empty:
            self.results = pd.DataFrame(columns=["value", "score", "rank"])
            return

        if method == "fuzzy":
            self.results = _rank_fuzzy(normalized_values, normalized_query, limit=limit, threshold=threshold)
        else:
            self.results = _rank_semantic(
                normalized_values,
                normalized_query,
                limit=limit,
                threshold=threshold,
                model_name=model_name,
            )

    def __call__(self) -> pd.DataFrame:
        return self.to_frame()

    def to_frame(self) -> pd.DataFrame:
        return self.results.copy()

    def sort_values(self) -> pd.Series:
        """Return ranked values ordered by descending similarity score."""
        return self.results["value"].reset_index(drop=True)

    def top_k(self, k: int) -> pd.Series:
        """Return the top-k most similar values."""
        if k <= 0:
            raise ValueError("k must be a positive integer")
        return self.results.head(k)["value"].reset_index(drop=True)

    def top_K(self, K: int) -> pd.Series:
        """Backward-compatible alias for top_k."""
        return self.top_k(K)


def rank_texts(
    values: list[str] | pd.Series,
    query: str,
    method: Literal["fuzzy", "semantic"] = DEFAULT_METHOD,
    limit: int | None = DEFAULT_LIMIT,
    threshold: float | None = None,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
) -> pd.DataFrame:
    """Rank text values against a query using fuzzy or semantic similarity."""
    return RankTexts(values, query, method=method, limit=limit, threshold=threshold, model_name=model_name)


def _normalize_values(values: list[str] | pd.Series) -> pd.Series:
    if isinstance(values, pd.Series):
        series = values.copy()
    elif isinstance(values, list):
        series = pd.Series(values)
    else:
        raise TypeError("values must be a list[str] or pandas.Series")

    if series.empty:
        return pd.Series(dtype="object")

    normalized = series.dropna().astype(str).reset_index(drop=True)
    return normalized


def _rank_fuzzy(
    values: pd.Series,
    query: str,
    *,
    limit: int | None,
    threshold: float | None,
) -> pd.DataFrame:
    score_cutoff = threshold if threshold is not None else 0.0
    choices = dict(enumerate(values.tolist()))
    requested_limit = len(choices) if limit is None else min(limit, len(choices))

    matches = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio,
        processor=None,
        limit=requested_limit,
        score_cutoff=score_cutoff,
    )

    records = [{"value": value, "score": float(score), "rank": rank} for rank, (value, score, _) in enumerate(matches, start=1)]
    return pd.DataFrame(records, columns=["value", "score", "rank"])


def _rank_semantic(
    values: pd.Series,
    query: str,
    *,
    limit: int | None,
    threshold: float | None,
    model_name: str,
) -> pd.DataFrame:
    embeddings = _get_or_create_embeddings(values, model_name=model_name)
    query_embedding = _encode_query(query, model_name=model_name)
    scores = cosine_similarity(embeddings, query_embedding.reshape(1, -1)).ravel()

    if threshold is not None:
        candidate_indices = np.flatnonzero(scores >= threshold)
    else:
        candidate_indices = np.arange(scores.shape[0])

    if candidate_indices.size == 0:
        return pd.DataFrame(columns=["value", "score", "rank"])

    ranked_indices = _select_top_indices(scores, candidate_indices, limit=limit)
    records = [
        {
            "value": values.iloc[index],
            "score": float(scores[index]),
            "rank": rank,
        }
        for rank, index in enumerate(ranked_indices, start=1)
    ]
    return pd.DataFrame(records, columns=["value", "score", "rank"])


def _select_top_indices(scores: np.ndarray, candidate_indices: np.ndarray, *, limit: int | None) -> np.ndarray:
    if limit is None or limit >= candidate_indices.size:
        order = np.argsort(scores[candidate_indices])[::-1]
        return candidate_indices[order]

    top_partition = np.argpartition(scores[candidate_indices], -limit)[-limit:]
    top_indices = candidate_indices[top_partition]
    order = np.argsort(scores[top_indices])[::-1]
    return top_indices[order]


def _get_or_create_embeddings(values: pd.Series, *, model_name: str) -> np.ndarray:
    cache_key = (model_name, _hash_values(values))
    cached_embeddings = _EMBEDDING_CACHE.get(cache_key)
    if cached_embeddings is not None:
        _EMBEDDING_CACHE.move_to_end(cache_key)
        return cached_embeddings

    model = _get_model(model_name)
    embeddings = model.encode(
        values.tolist(),
        batch_size=SEMANTIC_BATCH_SIZE,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=len(values) >= 10_000,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    _EMBEDDING_CACHE[cache_key] = embeddings
    if len(_EMBEDDING_CACHE) > SEMANTIC_CACHE_SIZE:
        _EMBEDDING_CACHE.popitem(last=False)
    return embeddings


def _encode_query(query: str, *, model_name: str) -> np.ndarray:
    model = _get_model(model_name)
    embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    return np.asarray(embedding, dtype=np.float32)


def _get_model(model_name: str):
    if model_name not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer

        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def _hash_values(values: pd.Series) -> str:
    digest = blake2b(digest_size=16)
    digest.update(str(len(values)).encode("utf-8"))
    for value in values.tolist():
        digest.update(value.encode("utf-8", errors="ignore"))
        digest.update(b"\x00")
    return digest.hexdigest()
