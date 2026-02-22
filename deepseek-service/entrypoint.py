import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.api_router import router


logging.basicConfig(
    level=logging.INFO,
    filename="logs/llm_log.log",
    filemode="w",
    format="%(asctime)s:%(levelname)s:%(message)s",
)

# ==========================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(
    router,
    # prefix="/api/v1/llm",
)
