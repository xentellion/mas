from dataclasses import dataclass


@dataclass(frozen=True)
class AlignmentScoring:
    gap_penalty: float = -1.0
    high_threshold: float = 0.80
    medium_threshold: float = 0.60
    high_score: float = 2.0
    medium_score: float = 1.0
    low_score: float = -2.0
    missing_score: float = -1.0
