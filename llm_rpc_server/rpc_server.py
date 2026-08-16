import os
import sys
import json
import time

__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import chromadb
import pika

from langchain_classic.chains import RetrievalQA
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma.vectorstores import Chroma

# ==============================

LLM: ChatOllama = None
EMBEDDINGS = OllamaEmbeddings(model="all-minilm:l6-v2")
VECTOR_STORE = Chroma(
    client=chromadb.HttpClient(
        host=os.environ["CHROMA"],
        port=8070,
    ),
    collection_name="ZE_TEST",
    embedding_function=EMBEDDINGS,
)

# ==============================


def func(prompt: str, model: str, temperature: float, cloud: bool = False):
    global LLM
    try:
        if LLM is None or LLM.model != model or LLM.temperature != temperature:
            LLM = ChatOllama(model=model, temperature=temperature)
        qa_chain = RetrievalQA.from_chain_type(
            llm=LLM, retriever=VECTOR_STORE.as_retriever()
        )
        return qa_chain.invoke({"query": prompt})["result"]
    # @TODO add proper exceptions
    except Exception as e:
        print(e)
        return None


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
