FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY proxy_agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY proxy_agent ./proxy_agent

EXPOSE 8000

CMD ["uvicorn", "proxy_agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
