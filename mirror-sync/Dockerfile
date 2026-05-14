FROM python:3.13-slim

WORKDIR /app

COPY mirror-sync/service.py /app/mirror-sync/service.py
COPY mirror-sync/runtime /app/mirror-sync/runtime

CMD ["python", "/app/mirror-sync/service.py"]
