import os
import sys

# To fix wrong Sqlite3 error in Chroma
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_classic.chains import RetrievalQA
from langchain_chroma.vectorstores import Chroma


# load_dotenv()
# TOKEN = os.getenv("DEEPSEEK_API_KEY")
MODEL=os.getenv("MODEL")

llm = ChatOllama(model=MODEL, temperature=0.3)
# embeddings = OllamaEmbeddings(model="deepseek-r1")

db = Chroma(
    collection_name="ZE_TEST",
    # embedding_function=embeddings,
    # host="0.0.0.0",
    host=os.environ["CHROMA"],
    port="8070"
)

# gigachat = GigachatSession()
app = FastAPI()


@app.get("/")
async def index():
    return {"response": "server_online"}


@app.post("/")
async def get_llm_response(prompt: str):
    return {"response": local_request(prompt)}


def local_request(prompt):
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=db.as_retriever())
    res = qa_chain.invoke({"query": prompt})
    return res["result"]
