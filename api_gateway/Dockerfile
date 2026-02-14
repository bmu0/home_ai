FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Кеш pip монтируется временно, не увеличивает размер образа
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
