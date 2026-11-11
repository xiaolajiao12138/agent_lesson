FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# 依赖文件先复制，业务代码变化时可以复用依赖层。
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY migrations ./migrations
COPY support_agent ./support_agent

USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "support_agent.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
