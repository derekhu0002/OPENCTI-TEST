FROM python:3.13-slim

WORKDIR /app

COPY mirror-sync/service.py /app/mirror-sync/service.py
COPY mirror-sync/sync_scope.json /app/mirror-sync/sync_scope.json
COPY mirror-sync/sync_scope.full.json /app/mirror-sync/sync_scope.full.json
COPY mirror-sync/runtime /app/mirror-sync/runtime

CMD ["python", "/app/mirror-sync/service.py"]
