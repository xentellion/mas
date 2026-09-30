from pydantic import BaseModel


class MetricComparedLists(BaseModel):
    origin: list[str]
    modeled: list[str]
