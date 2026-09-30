FROM python:3.12-slim-bullseye

WORKDIR /app

COPY /packages/shared /tmp/shared
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir /tmp/shared_models

COPY . .

EXPOSE 8100

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]