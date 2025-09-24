import chromadb
import json

chroma_client = chromadb.HttpClient(host="localhost", port=8070)
# chroma_client.delete_collection("ZE_TEST")
# collection = chroma_client.create_collection("ZE_TEST")
collection = chroma_client.get_collection("ZE_TEST")

collection.add(
    ids=[
        "id_0",
    ],
    documents=[
        """Для посадки на самолет местных рейсов после того, как заешел в аэропорт, необходимо провести следующие операции, в следующем порядке.
1. Пройти досмотр багажа
2. Проследовать на стойку регистрации и сдать багаж
3. Пройти личный досмотр
4. Дождаться начала посадки на рейс, на который был взят билет
5. Пройти на посадку

После того, как сошел с самолета, необходимо провести следующие операции, в следующем порядке.
1. Получить багаж
2. Пройти досмотр багажа
3. Пройти на Выход


Список существующих точек, к которым можно обращаться:
- Выход - Exit
- Вход - Entrance
- Ворота 1 - Gate_1
- Ворота 2 - Gate_2
- Получение багажа - Baggage_Reclaim
- Досмотр Багажа на входе - Security_Checkpoint_entrance
- Досмотр Багажа на выходе - Security_Checkpoint_exit"""
    ],
)

# collection.add(
#     ids=[
#         "rules_1",
#         "inters_1",
#         "inters_2",
#         "inters_3",
#         "inters_4",
#     ],
#     documents=[
#     ],
# )
# Точка Выход - Exit - координаты (59.0, 6.0)

# collection.add(
#     ids=["inters_8"],
#     documents=["Стол регистрации 1 - Registration_Desk_1"]
# )

res = collection.query(
    query_texts=["Перечисли все доступные точки"],
    # query_texts=["Closest point to (5, 5)"],
    n_results=10,
)
print(json.dumps(res, sort_keys=False, indent=4, ensure_ascii=False))
