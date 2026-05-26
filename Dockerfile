FROM python:3.8-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ---- Development ----
FROM base AS development
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]

# ---- Production ----
FROM base AS production
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4"]
