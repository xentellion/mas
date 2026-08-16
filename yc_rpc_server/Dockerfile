FROM python:3.13.3-slim-bullseye

RUN apt-get update && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && rm -rf /root/.cache/pip