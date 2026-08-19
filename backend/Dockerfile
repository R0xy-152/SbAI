# docs/13 §30：backend 服务 —— FastAPI + psycopg（PostgreSQL 存档）。
# 会话/存档数据落在容器内 volume（postgres_data），不写死主机路径。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GAL_PROVIDER=mock \
    GAL_SAVE_BACKEND=postgres \
    GAL_POSTGRES_DSN=postgresql://gal:gal@postgres:5432/gal

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg[binary]

COPY backend/ /app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
