# python -m pip install -e packages/shared
from fastapi import FastAPI
from schemas import MetricComparedLists

app = FastAPI()


@app.post("/count", response_model=int)
def count_strings(payload: MetricComparedLists) -> int:
    return len(payload.items)
