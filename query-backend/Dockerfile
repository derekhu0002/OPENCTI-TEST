FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN mkdir -p /app/query-backend /app/query-backend/runtime /app/mirror-sync/runtime

COPY query-backend/server.py /app/query-backend/server.py

EXPOSE 8088

CMD ["python", "/app/query-backend/server.py"]