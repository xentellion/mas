import os
import chromadb

# import json

collection_name = "ZE_TEST"
chroma_client = chromadb.HttpClient(host="localhost", port=8070)
try:
    chroma_client.delete_collection(collection_name)
except chromadb.errors.NotFoundError:
    print(f"Collection {collection_name} is not yet created")
collection = chroma_client.get_or_create_collection(collection_name)

documents = []

data_folder = "data"
for entry in os.listdir(data_folder):
    full_path = os.path.join(data_folder, entry)
    if not os.path.isfile(full_path):
        continue
    with open(full_path, "r") as f:
        documents.append(({"category": ".".join(entry.split(".")[:-1])}, f.read()))

documents = list(zip(*((x[0], x[1][0], x[1][1]) for x in enumerate(documents))))

collection.add(
    ids=list(map(lambda x: f"id_{x}", documents[0])),
    metadatas=list(documents[1]),
    documents=list(documents[2]),
)

# res = collection.query(
#     query_texts=[
#         "Список существующих точек, с которыми можно производить взаимодействия"
#     ],
#     n_results=1,
# )
# print(json.dumps(res, sort_keys=False, indent=4, ensure_ascii=False))
