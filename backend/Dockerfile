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
# docs-first 序章内容真相源（backend/app/script/prologue_content.py 运行时读取）。
COPY docs/story/Prologue.md /docs/story/Prologue.md

# Game static assets for the repo-root StaticFiles mount (app/main.py):
# dev 下 REPO_ROOT = 仓库根；容器内 REPO_ROOT = 容器根 /，
# 因此把三棵资源树拷到容器根（docs/13 Task 9 Step 3）。
COPY char/ /char/
COPY backgroud/ /backgroud/
COPY frontend-deprecated/ /frontend-deprecated/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
