from __future__ import annotations

from collections import OrderedDict
from hashlib import blake2b
from os import PathLike
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_METHOD: Literal["fuzzy", "semantic"] = "fuzzy"
DEFAULT_MODEL_NAME = "google/embeddinggemma-300m"
DEFAULT_LIMIT = None
SEMANTIC_BATCH_SIZE = 256
SEMANTIC_CACHE_SIZE = 4

_EMBEDDING_CACHE: OrderedDict[tuple[str, str, str], np.ndarray] = OrderedDict()
_MODEL_CACHE: dict[str, object] = {}

EmbeddingTask = Literal[
    "retrieval",
    "similarity",
    "classification",
    "clustering",
    "qa",
    "fact_check",
    "code_retrieval",
]


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
        embedding_task: EmbeddingTask = "similarity",
        output_csv: str | PathLike[str] | None = None,
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
        self.embedding_task = embedding_task
        self.source_values = normalized_values

        if normalized_values.empty:
            self.all_results = pd.DataFrame(columns=["annotation", "score", "rank"])
            self.results = pd.DataFrame(columns=["annotation", "score", "rank"])
            if output_csv is not None:
                self.to_csv(output_csv)
            return

        if method == "fuzzy":
            self.all_results = _rank_fuzzy(
                normalized_values,
                normalized_query,
            )
        else:
            self.all_results = _rank_semantic(
                normalized_values,
                normalized_query,
                model_name=model_name,
                embedding_task=embedding_task,
            )

        self.results = _filter_ranked_results(
            self.all_results,
            limit=limit,
            threshold=threshold,
        )

        if output_csv is not None:
            self.to_csv(output_csv)

    def __call__(self) -> pd.DataFrame:
        return self.to_frame()

    def to_frame(self) -> pd.DataFrame:
        return self.results.copy()

    def to_full_frame(self) -> pd.DataFrame:
        return self.all_results.copy()

    def to_csv(self, path: str | PathLike[str], *, index: bool = False, export_all: bool = True) -> Path:
        output_path = _coerce_output_path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame = self.all_results if export_all else self.results
        frame = frame.rename(columns={"rank": "semantic_rank"})
        frame.to_csv(output_path, index=index)
        return output_path

    def sort_values(self) -> pd.Series:
        return self.results["annotation"].reset_index(drop=True)

    def top_k(self, k: int) -> pd.Series:
        if k <= 0:
            raise ValueError("k must be a positive integer")
        return self.results.head(k)["annotation"].reset_index(drop=True)

    def top_K(self, K: int) -> pd.Series:
        return self.top_k(K)


def rank_texts(
    values: list[str] | pd.Series,
    query: str,
    method: Literal["fuzzy", "semantic"] = DEFAULT_METHOD,
    limit: int | None = DEFAULT_LIMIT,
    threshold: float | None = None,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    embedding_task: EmbeddingTask = "retrieval",
    output_csv: str | PathLike[str] | None = None,
) -> pd.DataFrame:
    """Return ranked texts and optionally export the full ordered input set to CSV."""
    return RankTexts(
        values,
        query,
        method=method,
        limit=limit,
        threshold=threshold,
        model_name=model_name,
        embedding_task=embedding_task,
        output_csv=output_csv,
    ).to_frame()


def _normalize_values(values: list[str] | pd.Series) -> pd.Series:
    if isinstance(values, pd.Series):
        series = values.copy()
    elif isinstance(values, list):
        series = pd.Series(values)
    else:
        raise TypeError("values must be a list[str] or pandas.Series")

    if series.empty:
        return pd.Series(dtype="object")

    return series.dropna().astype(str).reset_index(drop=True)


def _coerce_output_path(path: str | PathLike[str]) -> Path:
    output_path = Path(path)
    if not str(output_path).strip():
        raise ValueError("output_csv must be a non-empty path")
    return output_path


def _rank_fuzzy(
    values: pd.Series,
    query: str,
) -> pd.DataFrame:
    choices = dict(enumerate(values.tolist()))

    matches = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio,
        processor=None,
        limit=len(choices),
        score_cutoff=0.0,
    )

    records = [{"annotation": value, "score": float(score), "rank": rank} for rank, (value, score, _) in enumerate(matches, start=1)]
    return pd.DataFrame(records, columns=["annotation", "score", "rank"])


def _rank_semantic(
    values: pd.Series,
    query: str,
    *,
    model_name: str,
    embedding_task: EmbeddingTask,
) -> pd.DataFrame:
    embeddings = _get_or_create_embeddings(
        values,
        model_name=model_name,
        embedding_task=embedding_task,
    )
    query_embedding = _encode_query(
        query,
        model_name=model_name,
        embedding_task=embedding_task,
    )
    scores = cosine_similarity(embeddings, query_embedding.reshape(1, -1)).ravel()
    ranked_indices = np.argsort(scores)[::-1]
    records = [
        {
            "annotation": values.iloc[index],
            "score": float(scores[index]),
            "rank": rank,
        }
        for rank, index in enumerate(ranked_indices, start=1)
    ]
    return pd.DataFrame(records, columns=["annotation", "score", "rank"])


def _filter_ranked_results(
    ranked_results: pd.DataFrame,
    *,
    limit: int | None,
    threshold: float | None,
) -> pd.DataFrame:
    filtered = ranked_results

    if threshold is not None:
        filtered = filtered[filtered["score"] >= threshold]

    if limit is not None:
        filtered = filtered.head(limit)

    if filtered.empty:
        return pd.DataFrame(columns=["annotation", "score", "rank"])

    filtered = filtered.reset_index(drop=True).copy()
    filtered["rank"] = np.arange(1, len(filtered) + 1)
    return filtered


def _get_or_create_embeddings(
    values: pd.Series,
    *,
    model_name: str,
    embedding_task: EmbeddingTask,
) -> np.ndarray:
    cache_key = (model_name, embedding_task, _hash_values(values))
    cached_embeddings = _EMBEDDING_CACHE.get(cache_key)
    if cached_embeddings is not None:
        _EMBEDDING_CACHE.move_to_end(cache_key)
        return cached_embeddings

    model = _get_model(model_name)
    inputs = [_format_document_text(v, embedding_task) for v in values.tolist()]
    embeddings = model.encode(
        inputs,
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


def _encode_query(
    query: str,
    *,
    model_name: str,
    embedding_task: EmbeddingTask,
) -> np.ndarray:
    model = _get_model(model_name)
    formatted_query = _format_query_text(query, embedding_task)
    embedding = model.encode(
        [formatted_query],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    return np.asarray(embedding, dtype=np.float32)


def _format_query_text(text: str, task: EmbeddingTask) -> str:
    text = text.strip()

    if task == "retrieval":
        return f"task: search result | query: {text}"
    if task == "similarity":
        return f"task: sentence similarity | query: {text}"
    if task == "classification":
        return f"task: classification | query: {text}"
    if task == "clustering":
        return f"task: clustering | query: {text}"
    if task == "qa":
        return f"task: question answering | query: {text}"
    if task == "fact_check":
        return f"task: fact checking | query: {text}"
    if task == "code_retrieval":
        return f"task: code retrieval | query: {text}"

    return text


def _format_document_text(text: str, task: EmbeddingTask) -> str:
    text = text.strip()

    if task in {"retrieval", "qa", "fact_check", "code_retrieval"}:
        return f"title: none | text: {text}"

    return text


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
