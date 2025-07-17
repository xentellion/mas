import chromadb
import json

chroma_client = chromadb.HttpClient(host="localhost", port=8070)
# collection = chroma_client.create_collection("ZE_TEST")
collection = chroma_client.get_collection("ZE_TEST")

collection.add(
    ids=[
        "id3",
        "id4",
    ],
    documents=[
        "(x=1, y=1)",
        "(x=2, y=3)",
    ],
)

res = collection.query(
    query_texts=["Closest point to (5, 5)"],
    n_results=2,
)
print(json.dumps(res, sort_keys=False, indent=4))
