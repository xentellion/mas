import os
import sys

__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, "config", ".env")
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("API_KEY")
URL = os.getenv("URL")
PROJECT_ID = os.getenv("PROJECT")

MODEL = os.getenv("MODEL")
MODEL_URI = f"gpt://{PROJECT_ID}/{MODEL}"

EMB_DOC_URI = f"emb://{PROJECT_ID}/text-search-doc/latest"
EMB_QUERY_URI = f"emb://{PROJECT_ID}/text-search-query/latest"

COLLECTION_NAME = "YANDEX_TEST"


yandex_client = OpenAI(api_key=API_KEY, base_url=URL)
chroma_client = client = chromadb.HttpClient(
    host="firewalker.space",
    port=8070,
)

try:
    chroma_client.delete_collection(COLLECTION_NAME)
    print(f"Collection {COLLECTION_NAME} deleted")
except chromadb.errors.NotFoundError:
    print(f"Collection {COLLECTION_NAME} is not yet created")
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=None,
)


def get_yandex_embedding(text: str, model_uri: str) -> list:
    response = yandex_client.embeddings.create(
        input=[text],
        model=model_uri,
        encoding_format="float",
    )
    return response.data[0].embedding


def populate_database():
    documents = []

    data_folder = "../chromadb-service/data"
    for entry in os.listdir(data_folder):
        full_path = os.path.join(data_folder, entry)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, "r") as f:
            documents.append(({"category": ".".join(entry.split(".")[:-1])}, f.read()))
    print(f"Data collected: {len(documents)}")
    embeddings = [get_yandex_embedding(text, EMB_DOC_URI) for _, text in documents]
    documents = list(zip(*((x[0], x[1][0], x[1][1]) for x in enumerate(documents))))
    collection.add(
        ids=list(map(lambda x: f"id_{x}", documents[0])),
        embeddings=embeddings,
        metadatas=list(documents[1]),
        documents=list(documents[2]),
    )
    print("Complete")


populate_database()
