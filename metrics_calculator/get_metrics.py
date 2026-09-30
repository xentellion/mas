import json
import hashlib

import numpy as np

from redis.asyncio import Redis
from starlette.concurrency import run_in_threadpool
from sentence_transformers import SentenceTransformer

from alignment_scoring import AlignmentScoring


async def transform(text: str, redis: Redis, model: SentenceTransformer):
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    redis_key = f"embedding:{text_hash}"

    cached_embedding = await redis.hget(redis_key, "embedding")
    if cached_embedding is not None:
        return json.loads(cached_embedding)

    embedding = await run_in_threadpool(
        lambda: model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()
    )

    await redis.hset(
        redis_key,
        mapping={
            "text": text,
            "embedding": json.dumps(embedding),
        },
    )
    return embedding


def build_alignment_matrices(
    vectors_origin: tuple[list[float]],
    vectors_modeled: tuple[list[float]],
    scoring: AlignmentScoring,
):
    rows, cols = len(vectors_origin), len(vectors_modeled)

    if rows and cols:
        origin = np.asarray(vectors_origin, dtype=np.float32)
        modeled = np.asarray(vectors_modeled, dtype=np.float32)

        denominator = (
            np.linalg.norm(origin, axis=1)[:, None]
            * np.linalg.norm(modeled, axis=1)[None, :]
        )
        similarities = np.divide(
            origin @ modeled.T,
            denominator,
            out=np.full((rows, cols), np.nan, dtype=np.float32),
            where=denominator != 0,
        )

        scores = np.select(
            [
                similarities > scoring.high_threshold,
                similarities >= scoring.medium_threshold,
            ],
            [scoring.high_score, scoring.medium_score],
            default=scoring.low_score,
        ).astype(np.float32)
        scores[~np.isfinite(similarities)] = scoring.missing_score
    else:
        scores = np.empty((rows, cols), dtype=np.float32)

    alignment = np.zeros((rows + 1, cols + 1), dtype=np.float32)
    alignment[:, 0] = np.arange(rows + 1) * scoring.gap_penalty
    alignment[0, :] = np.arange(cols + 1) * scoring.gap_penalty

    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            alignment[i, j] = max(
                alignment[i - 1, j - 1] + scores[i - 1, j - 1],
                alignment[i - 1, j] + scoring.gap_penalty,
                alignment[i, j - 1] + scoring.gap_penalty,
            )

    return scores.tolist(), alignment.tolist()


def needleman_wunsch_similarity(
    similarities: list[list[float]],
    alignment: list[list[float]],
    scoring: AlignmentScoring,
):
    scores_array = np.asarray(similarities, dtype=np.float32)
    alignment_array = np.asarray(alignment, dtype=np.float32)

    i, j = scores_array.shape
    matches_and_substitutions = 0
    alignment_length = 0

    while i > 0 or j > 0:
        current = alignment_array[i, j]

        # Диагональный шаг: совпадение или замена.
        if (
            i > 0
            and j > 0
            and np.isclose(
                current,
                alignment_array[i - 1, j - 1] + scores_array[i - 1, j - 1],
            )
        ):
            pair_score = scores_array[i - 1, j - 1]
            if pair_score in (scoring.high_score, scoring.medium_score):
                matches_and_substitutions += 1
            i -= 1
            j -= 1

        # Вертикальный или горизонтальный шаг: пропуск.
        elif i > 0 and np.isclose(
            current,
            alignment_array[i - 1, j] + scoring.gap_penalty,
        ):
            i -= 1
        else:
            j -= 1

        alignment_length += 1

    if alignment_length == 0:
        return 0.0

    return round((matches_and_substitutions / alignment_length) * 100.0, 4)
