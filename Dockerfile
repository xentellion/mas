FROM python:3.13.3-slim-bullseye AS intermediate

RUN apt update && \
    apt install -y wget git openssh-client && \
    useradd -u 1000 1000 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /mas
ADD . .

# ########################################################

FROM python:3.13.3-slim-bullseye

COPY --from=intermediate /mas /srv/mas
WORKDIR /srv/mas

RUN pip install -r requirements.txt

ENTRYPOINT ["python3", "__main__.py"]
