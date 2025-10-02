import json
import chromadb


chroma_client = chromadb.HttpClient(host="localhost", port=8070)
chroma_client.delete_collection("ZE_TEST")
collection = chroma_client.create_collection("ZE_TEST")
collection = chroma_client.get_collection("ZE_TEST")

with open("data/rules.txt", "r", encoding="UTF-8") as f:
    data = f.read()

collection.add(ids=["id_0"], documents=[data])

res = collection.query(
    query_texts=["Перечисли все доступные точки взаимодействия"],
    n_results=10,
)
print(json.dumps(res, sort_keys=False, indent=4, ensure_ascii=False))
