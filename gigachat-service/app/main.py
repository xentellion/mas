import os
import sys

# To fix wrong Sqlite3 error in Chroma
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI

from langchain_classic.chains import RetrievalQA
from langchain_chroma.vectorstores import Chroma
from langchain_gigachat.chat_models import GigaChat

from langchain_huggingface import HuggingFaceEmbeddings


load_dotenv()
TOKEN = os.getenv("TOKEN_GIGACHAT")
CERT_PATH_DEFAULT = "app/ca-gigachat.pem"


llm = GigaChat(
    credentials=TOKEN,
    verify_ssl_certs=False,
)
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
async def get_llm_response(model: str, prompt: str):
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, retriever=vector_store.as_retriever()
    )
    res = qa_chain.invoke({"query": prompt})
    return res["result"]
