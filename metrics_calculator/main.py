import os
import json
from contextlib import asynccontextmanager


from fastapi import FastAPI, Request, HTTPException
from redis.asyncio import Redis
from sentence_transformers import SentenceTransformer
from pydantic import ValidationError

from shared.schemas import MetricComparedLists, MetricResponse, AlignmentScoring
from get_metrics import needleman_wunsch_alignment, build_alignment_matrices, transform


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_config(path: str = "scoring.json"):
    config_path = os.path.join(
        os.path.dirname(__file__),
        "data",
        path,
    )
    try:
        with open(config_path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Scoring configuration file not found: {config_path}"
        ) from e
    except PermissionError as e:
        raise RuntimeError(
            f"Permission denied reading scoring configuration: {config_path}"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Invalid JSON in scoring configuration: {config_path}"
        ) from e
    except OSError as e:
        raise RuntimeError(
            f"Could not read scoring configuration: {config_path}"
        ) from e


def save_config(scoring: AlignmentScoring, path: str = "scoring.json"):
    config_path = os.path.join(os.path.dirname(__file__), "data", path)
    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(scoring.model_dump(), file, indent=2)


def read_scoring(path: str = "scoring.json"):
    return AlignmentScoring.model_validate(load_config(path))


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        scoring = AlignmentScoring(**load_config())
    except Exception as e:
        raise RuntimeError(
            f"Failed to load scoring configuration during startup: {e}"
        ) from e
    app.state.scoring = scoring

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


@app.get("/metrics", response_model=AlignmentScoring)
def get_scoring(request: Request):
    try:
        scoring = read_scoring()
    except (RuntimeError, ValidationError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read scoring configuration: {e}",
        ) from e
    return scoring


@app.post("/change")
def reset_metrics(scoring: AlignmentScoring, request: Request):
    try:
        save_config(scoring)
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save scoring configuration: {e}",
        ) from e

    request.app.state.scoring = scoring
    return {"status": "Success"}


@app.post("/count", response_model=MetricResponse)
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

    scores, alignment, matches, traceback, cosine_similarities = (
        build_alignment_matrices(vectors_origin, vectors_modeled, scoring)
    )

    match_rate, cosine_similarities = needleman_wunsch_alignment(
        matches,
        traceback,
        cosine_similarities,
    )

    return MetricResponse(
        match_rate=match_rate,
        cosine_similarities=cosine_similarities,
    )
