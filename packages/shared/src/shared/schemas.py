from pydantic import BaseModel


class MetricComparedLists(BaseModel):
    origin: list[str]
    modeled: list[str]


class MetricResponse(BaseModel):
    match_rate: float
    cosine_similarities: list[float | None]


class AlignmentScoring(BaseModel):
    gap_penalty: float = -1.0
    high_threshold: float = 0.80
    medium_threshold: float = 0.60
    high_score: float = 2.0
    medium_score: float = 1.0
    low_score: float = -2.0
    missing_score: float = -1.0
