import os
import sys

# To fix wrong Sqlite3 error in Chroma
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_gigachat.chat_models import GigaChat
from langchain.chains import RetrievalQA
from langchain_chroma.vectorstores import Chroma

# from .api.gigachat_api import GigachatSession


load_dotenv()
TOKEN = os.getenv("TOKEN_GIGACHAT")
CERT_PATH_DEFAULT = "app/ca-gigachat.pem"


llm = GigaChat(
    credentials=TOKEN,
    verify_ssl_certs=False,
)

db = Chroma(
    collection_name="ZE_TEST",
    # embedding_function=embeddings,
    # host="0.0.0.0",
    host=os.environ["CHROMA"],
    port="8070",
)

# gigachat = GigachatSession()
app = FastAPI()


@app.get("/")
async def index():
    return {"response": "server_online"}


@app.post("/")
async def get_llm_response(prompt: str, model):
    return {"response": local_request(prompt)}


def local_request(prompt):
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=db.as_retriever())
    res = qa_chain.invoke({"query": prompt})
    return res["result"]
