from fastapi import FastAPI
from .api.gigachat_api import GigachatSession


gigachat = GigachatSession()
app = FastAPI()


@app.get("/")
async def index():
    return {"response": "server_online"}


@app.post("/")
async def get_llm_response(role, prompt: str):
    return {"response": gigachat.request(role, prompt)}
