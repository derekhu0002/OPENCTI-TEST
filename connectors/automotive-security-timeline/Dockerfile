FROM python:3.12-alpine
ENV CONNECTOR_TYPE=EXTERNAL_IMPORT

COPY src /opt/opencti-connector-automotive-security-timeline
WORKDIR /opt/opencti-connector-automotive-security-timeline

RUN apk update && apk upgrade && \
    apk --no-cache add git build-base libmagic libffi-dev libxml2-dev libxslt-dev && \
    pip3 install --no-cache-dir -r requirements.txt && \
    apk del git build-base && \
    rm -rf /var/cache/apk/*

ENTRYPOINT ["python", "main.py"]