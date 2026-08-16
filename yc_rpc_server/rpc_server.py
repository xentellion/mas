import os
import sys
import json
import pika
import time

__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
URL = os.getenv("URL")
PROJECT_ID = os.getenv("PROJECT")

MODEL = os.getenv("MODEL")
MODEL_URI = f"gpt://{PROJECT_ID}/{MODEL}"

EMB_DOC_URI = f"emb://{PROJECT_ID}/text-search-doc/latest"
EMB_QUERY_URI = f"emb://{PROJECT_ID}/text-search-query/latest"


yandex_client = OpenAI(api_key=API_KEY, base_url=URL)
chroma_client = client = chromadb.HttpClient(
    host="firewalker.space",
    port=8070,
)

collection = chroma_client.get_or_create_collection(
    name="YANDEX_TEST",
    embedding_function=None,
)


def get_yandex_embedding(text: str, model_uri: str) -> list:
    response = yandex_client.embeddings.create(
        input=[text],
        model=model_uri,
        encoding_format="float",
    )
    return response.data[0].embedding


def query_rag_system(user_question: str):
    query_embedding = get_yandex_embedding(user_question, EMB_QUERY_URI)

    search_results = collection.query(query_embeddings=[query_embedding], n_results=3)

    # It can be used to collect several relevant documents but atp it is not exactly required.
    retrieved_context = (
        search_results["documents"][0][0]
        if search_results["documents"]
        else "No context."
    )

    user_prompt = f"Context:\n{retrieved_context}\n\nQuestion:\n{user_question}"

    response = yandex_client.chat.completions.create(
        model=MODEL_URI,
        messages=[
            # {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def func(prompt: str, model: str, temperature: float, cloud: bool = False):
    return query_rag_system(prompt)


def on_request(ch, method, props, body):
    print(body)
    response = func(**json.loads(body.decode("utf-8")))
    print(response)
    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=str(response),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)


def rmq_connect():
    while True:
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                )
            )
        except pika.exceptions.AMQPConnectionError as e:
            print(f"RabbitMQ connection failed: {e}; retrying in 5s")
            time.sleep(5)


def start_consumer():
    while True:
        connection = rmq_connect()
        channel = connection.channel()

        channel.queue_declare(queue="rpc_queue")

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue="rpc_queue", on_message_callback=on_request)
        print(" [x] Awaiting RPC requests")
        try:
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection lost: {e}; reconnecting...")
            try:
                connection.close()
            except Exception:
                pass
            time.sleep(1)


if __name__ == "__main__":
    start_consumer()
