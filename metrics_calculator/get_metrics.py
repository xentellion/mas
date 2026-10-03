import hashlib
import json

import numpy as np
from redis.asyncio import Redis
from sentence_transformers import SentenceTransformer
from starlette.concurrency import run_in_threadpool

from shared.schemas import AlignmentScoring


DIAGONAL, UP, LEFT = 0, 1, 2


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
    vectors_origin: list[list[float]],
    vectors_modeled: list[list[float]],
    scoring: AlignmentScoring,
):
    rows, cols = len(vectors_origin), len(vectors_modeled)
    matches = np.zeros((rows, cols), dtype=bool)

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

        matches = np.isfinite(similarities) & (similarities >= scoring.medium_threshold)

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
        similarities = np.full((rows, cols), np.nan, dtype=np.float32)
        scores = np.empty((rows, cols), dtype=np.float32)

    alignment = np.zeros((rows + 1, cols + 1), dtype=np.float32)
    alignment[:, 0] = np.arange(rows + 1) * scoring.gap_penalty
    alignment[0, :] = np.arange(cols + 1) * scoring.gap_penalty

    traceback = np.zeros((rows + 1, cols + 1), dtype=np.uint8)
    traceback[1:, 0] = UP
    traceback[0, 1:] = LEFT

    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            candidates = np.array(
                [
                    alignment[i - 1, j - 1] + scores[i - 1, j - 1],
                    alignment[i - 1, j] + scoring.gap_penalty,
                    alignment[i, j - 1] + scoring.gap_penalty,
                ],
                dtype=np.float32,
            )

            # np.argmax chooses the first maximum: diagonal, then up, then left.
            move = int(np.argmax(candidates))
            alignment[i, j] = candidates[move]
            traceback[i, j] = move

    cosine_similarities = [
        [float(value) if np.isfinite(value) else None for value in row]
        for row in similarities
    ]

    return (
        scores.tolist(),
        alignment.tolist(),
        matches.tolist(),
        traceback.tolist(),
        cosine_similarities,
    )


def needleman_wunsch_alignment(
    matches: list[list[bool]],
    traceback: list[list[int]],
    cosine_similarities: list[list[float | None]],
) -> tuple[float, list[float | None]]:
    matches_array = np.asarray(matches, dtype=bool)
    traceback_array = np.asarray(traceback, dtype=np.uint8)
    similarities_array = np.asarray(cosine_similarities, dtype=np.float32)

    i, j = traceback_array.shape[0] - 1, traceback_array.shape[1] - 1
    matched_columns = 0
    aligned_similarities = []

    while i > 0 or j > 0:
        move = traceback_array[i, j]

        if move == DIAGONAL:
            similarity = similarities_array[i - 1, j - 1]
            aligned_similarities.append(
                float(similarity) if np.isfinite(similarity) else None
            )
            if matches_array[i - 1, j - 1]:
                matched_columns += 1
            i -= 1
            j -= 1
        elif move == UP:
            aligned_similarities.append(None)
            i -= 1
        else:
            aligned_similarities.append(None)
            j -= 1

    aligned_similarities.reverse()
    alignment_length = len(aligned_similarities)

    match_rate = (
        round((matched_columns / alignment_length) * 100.0, 4)
        if alignment_length
        else 0.0
    )
    return match_rate, aligned_similarities
