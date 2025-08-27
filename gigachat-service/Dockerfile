FROM python:3.13.3-slim-bullseye

RUN apt-get update && \
    apt-get install -y sqlite3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && rm -rf /root/.cache/pip
# uvicorn app.main:app --reload --host 0.0.0.0 --port 81
