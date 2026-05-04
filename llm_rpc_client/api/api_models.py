from pydantic import BaseModel


class Data(BaseModel):
    prompt: str
    model: str
    temperature: float = 0.3
    cloud: bool = False
