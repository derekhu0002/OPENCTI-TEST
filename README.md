# OpenCTI Threat Intelligence Platform

## What This Project Builds

This repository builds a complete local OpenCTI threat-intelligence system on Docker Compose.

After startup, the system provides:

- an OpenCTI core platform for storing, linking, searching, and operating on threat-intelligence data;
- the required infrastructure services behind OpenCTI, including Redis, Elasticsearch, MinIO, and RabbitMQ;
- a local HTTPS entrypoint through Caddy at `https://localhost`;
- a set of built-in OpenCTI import/export/analysis connectors;
- a set of external threat-intelligence connectors for ingesting public and vendor threat feeds;
- an additional custom connector, `Automotive Security Timeline`;
- an `xtm-composer` container for connector orchestration and management.

In short: this project is not just a demo compose file. It is a runnable local cyber threat intelligence platform with data ingestion, connector orchestration, TLS access, backup tooling, and architecture-level test coverage.

## System Overview

The deployed system is composed of four logical layers:

1. Access layer: Caddy exposes OpenCTI on local HTTPS.
2. Platform layer: OpenCTI provides the main UI, GraphQL API, and intelligence data model.
3. Infrastructure layer: Redis, Elasticsearch, MinIO, and RabbitMQ provide queueing, storage, indexing, and object storage.
4. Integration layer: multiple connectors import, enrich, export, or manage intelligence flows.

The modeled connector set is aligned with [design/KG/SystemArchitecture.json](design/KG/SystemArchitecture.json).

## Included Capabilities

This project currently includes these threat-intelligence connectors:

- MITRE ATT&CK
- NIST NVD CVE
- Google Threat Intelligence (GTI)
- CrowdStrike Falcon Intelligence
- Ransomware.live
- CISA Known Exploited Vulnerabilities (KEV)
- Mandiant
- ThreatFox
- MISP Intel
- Automotive Security Timeline

It also includes the standard OpenCTI file import/export and analysis connectors needed for day-to-day platform operation.

## How To Use This System

### 1. Prepare Environment

Copy or update `.env` with the values you want to use for local startup.

Important variables include:

- `OPENCTI_BASE_URL`
- `OPENCTI_ADMIN_EMAIL`
- `OPENCTI_ADMIN_PASSWORD`
- `OPENCTI_ADMIN_TOKEN`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `RABBITMQ_DEFAULT_USER`
- `RABBITMQ_DEFAULT_PASS`

By default, `.env` enables the `threat-intel-connectors` compose profile, so a normal startup will also launch the default threat-intelligence connectors.

### 2. Start The Platform

Start the full stack with:

```powershell
docker compose up -d
```

After startup, OpenCTI is exposed through:

```text
https://localhost
```

If your browser does not trust the local certificate, import Caddy's local root CA certificate from the running `caddy` container into the Windows Current User trusted root store.

### 3. Sign In To OpenCTI

Use the admin account from `.env`:

- username: `OPENCTI_ADMIN_EMAIL`
- password: `OPENCTI_ADMIN_PASSWORD`

Once logged in, you can:

- browse entities and relationships in the OpenCTI knowledge graph;
- search indicators, malware, campaigns, vulnerabilities, and reports;
- monitor connector status;
- review imported intelligence from the configured feeds;
- operate on cases, reports, and investigative workflows.

### 4. Use Connectors

Most threat-intelligence connectors in this repository start automatically with the default profile.

Special handling applies to these connectors:

- `connector-misp-intel` is intentionally isolated behind the dedicated `misp-intel` profile because it needs a real MISP endpoint, API key, and live stream configuration.
- `connector-cve` can start even when `CVE_API_KEY` is blank because the compose definition falls back to a non-empty placeholder key. This keeps the container running during formal startup, but real NVD data retrieval still requires a valid API key.

Start MISP Intel explicitly when its real runtime parameters are available:

```powershell
docker compose --profile misp-intel up -d connector-misp-intel
```

### 5. Stop Or Restart Without Losing Data

For no-data-loss lifecycle operations, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Stop
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Start
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Restart
```

These commands only stop or restart containers. They do not delete Docker volumes.

If you need to recreate containers without deleting persisted data, use:

```powershell
docker compose down
docker compose up -d
```

Do not add `-v` unless you explicitly want Docker to remove persisted data.

## Backup And Recovery-Oriented Operations

Use the backup script to snapshot data volumes and deployment metadata:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1
```

The script will:

- detect whether the stack is currently running;
- stop the stack with `docker compose stop` for a consistent backup;
- export every Docker volume created by the compose project into `backups/<timestamp>/volumes`;
- copy `.env`, compose files, `Caddyfile`, and `rabbitmq.conf` into `backups/<timestamp>/metadata`;
- restart the stack if it was running before the backup started.

To preview backup actions without changing anything:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1 -WhatIf
```

To restore the latest backup back into the current workspace:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore-opencti.ps1
```

To restore a specific backup directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore-opencti.ps1 -BackupPath .\backups\20260426-120000
```

The restore script will:

- stop and remove the current Compose stack with `docker compose down`;
- restore metadata files from `backups/<timestamp>/metadata` back into the repository root;
- recreate each archived Docker volume from `backups/<timestamp>/volumes`;
- restart the stack if it was running before the restore started.

To preview restore actions without changing anything:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore-opencti.ps1 -WhatIf
```

## Operational Notes

- `threat-intel-connectors` is enabled by default through `.env`.
- `misp-intel` is a separate profile and must be started explicitly.
- A blank `CVE_API_KEY` no longer causes `connector-cve` to crash-loop during startup.
- Some vendor-backed connectors may start successfully but still require valid third-party credentials before they can ingest real data.

## Validation And Architecture Consistency

Architecture and runtime consistency are validated by:

```powershell
d:/Projects/OPENCTI-TEST/.venv/Scripts/python.exe -m pytest tests/test_architecture_connector_support.py -vv
```

This suite checks that the connectors declared in the architecture graph are actually represented in the repository and, where applicable, can reach real Docker runtime coverage.

## Reference Documentation

- OpenCTI Docker installation: [OpenCTI documentation](https://docs.opencti.io/latest/deployment/installation/#using-docker)
- Architecture graph: [design/KG/SystemArchitecture.json](design/KG/SystemArchitecture.json)
- Acceptance suite: [tests/test_architecture_connector_support.py](tests/test_architecture_connector_support.py)

## Community

If you need product-level support or want to follow upstream development:

- Bugs and feature requests: [OpenCTI GitHub issues](https://github.com/OpenCTI-Platform/opencti/issues)
- Discussion: [Filigran community Slack](https://community.filigran.io)
- Contact: `contact@opencti.io`

## About OpenCTI

OpenCTI is a threat intelligence platform designed and developed by [Filigran](https://filigran.io).

<a href="https://filigran.io" alt="Filigran"><img src="https://github.com/OpenCTI-Platform/opencti/raw/master/.github/img/logo_filigran.png" width="300" /></a>