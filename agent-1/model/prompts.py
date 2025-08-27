from pydantic import BaseModel


class Prompts(BaseModel):
    prompt_departing: str
    prompt_arriving: str
