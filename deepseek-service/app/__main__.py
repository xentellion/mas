import os
import sys
import logging

# To fix wrong Sqlite3 error in Chroma
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import chromadb

from fastapi import FastAPI
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_classic.chains import RetrievalQA
from langchain_chroma.vectorstores import Chroma

logging.basicConfig(
    level=logging.INFO,
    filename="logs/llm_log.log",
    filemode="w",
    format="%(asctime)s:%(levelname)s:%(message)s",
)


llm: ChatOllama = None

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

vector_store = Chroma(
    client=chromadb.HttpClient(
        host=os.environ["CHROMA"],
        port=8070,
    ),
    collection_name="ZE_TEST",
    embedding_function=embeddings,
)

app = FastAPI()


@app.get("/")
async def index():
    return {"response": "server_online"}


@app.post("/")
async def get_llm_response(prompt: str, model: str = None):
    try:
        response = local_request(prompt)
    except Exception as e:
        logging.error(f"Error getting a request from a model: {e}")
        response = None
    return {"response": response}


@app.post("/swap")
async def swap_model(model: str, temperature: float = 0.3):
    global llm
    logging.info(f"Changing model to {model}")
    try:
        llm = ChatOllama(model=model, temperature=temperature)
    except Exception as e:
        logging.error(f"Error changing a model: {e}")
        llm = None
    return {"response": llm is not None}


def local_request(prompt):
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, retriever=vector_store.as_retriever()
    )
    res = qa_chain.invoke({"query": prompt})
    return res["result"]
