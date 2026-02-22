import os
import sys
import json

__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import chromadb
import pika

from langchain_classic.chains import RetrievalQA
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma.vectorstores import Chroma

# ==============================

llm: ChatOllama = None
embeddings = OllamaEmbeddings(model="all-minilm:l6-v2")
vector_store = Chroma(
    client=chromadb.HttpClient(
        host=os.environ["CHROMA"],
        port=8070,
    ),
    collection_name="ZE_TEST",
    embedding_function=embeddings,
)
# ==============================

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="rabbitmq",
        # host="localhost",
    )
)
channel = connection.channel()
channel.queue_declare(queue="rpc_queue")


def func(prompt: str, model: str, temperature: float, cloud: bool = False):
    global llm
    try:
        if llm is None or llm.model != model or llm.temperature != temperature:
            llm = ChatOllama(model=model, temperature=temperature)
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, retriever=vector_store.as_retriever()
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


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="rpc_queue", on_message_callback=on_request)

print(" [x] Awaiting RPC requests")
channel.start_consuming()
