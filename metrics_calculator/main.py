import os
import json
from contextlib import asynccontextmanager


from fastapi import FastAPI, Request
from redis.asyncio import Redis
from sentence_transformers import SentenceTransformer

from shared.schemas import MetricComparedLists
from alignment_scoring import AlignmentScoring
from get_metrics import needleman_wunsch_similarity, build_alignment_matrices, transform

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    config_path = os.path.join(
        os.path.dirname(__file__),
        "data",
        "scoring.json",
    )
    with open(config_path, encoding="utf-8") as file:
        scoring_config = json.load(file)
    app.state.scoring = AlignmentScoring(**scoring_config)

    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )
    await client.ping()
    app.state.redis = client
    app.state.model = SentenceTransformer(MODEL_NAME)
    app.state.model.max_seq_length = 256

    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(lifespan=lifespan)


@app.post("/count", response_model=float)
async def count_strings(payload: MetricComparedLists, request: Request) -> int:
    redis = request.app.state.redis
    scoring = request.app.state.scoring
    model = request.app.state.model

    vectors_origin = tuple(
        [await transform(text, redis, model) for text in payload.origin]
    )
    vectors_modeled = tuple(
        [await transform(text, redis, model) for text in payload.modeled]
    )

    similarities, alignment = build_alignment_matrices(
        vectors_origin,
        vectors_modeled,
        scoring,
    )
    return needleman_wunsch_similarity(
        similarities,
        alignment,
        scoring,
    )
