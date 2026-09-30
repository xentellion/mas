FROM python:3.12-slim-bullseye

WORKDIR /app

COPY --from=shared / /tmp/shared
RUN pip install --no-cache-dir /tmp/shared

COPY . .
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8100