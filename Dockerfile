FROM python:3.13.3-slim-bullseye

RUN apt update && \
    apt install -y git && \
    useradd -u 1000 1000 && \
    rm -rf /var/lib/apt/lists/*

USER 1000

ENTRYPOINT ["python3", "__main__.py"]