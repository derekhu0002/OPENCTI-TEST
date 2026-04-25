# OpenCTI Docker deployment

## Documentation

You can find the detailed documentation about the Docker installation in the [OpenCTI documentation space](https://docs.opencti.io/latest/deployment/installation/#using-docker).

## Local HTTPS

This workspace can expose OpenCTI through a local Caddy reverse proxy at `https://localhost`.
If your browser reports the certificate as untrusted, import Caddy's local root CA certificate from the running `caddy` container into the Windows Current User trusted root store.

## Threat Intel Connectors

The workspace now carries runtime definitions for the threat-intelligence connectors modeled in `design/KG/SystemArchitecture.json`: MITRE ATT&CK, NIST NVD CVE, Google Threat Intelligence (GTI), CrowdStrike Falcon Intelligence, Ransomware.live, CISA KEV, Mandiant, ThreatFox, and MISP Intel.

The threat-intelligence connectors that can run with empty or public-feed credentials are enabled by default through the `threat-intel-connectors` profile in `.env`, so a plain `docker compose up -d` starts `connector-threatfox` and the other modeled connectors in that set. `connector-misp-intel` is intentionally isolated behind the dedicated `misp-intel` profile because it requires a real MISP endpoint, API key, and live stream configuration; start it explicitly with `docker compose --profile misp-intel up -d connector-misp-intel` when those values are ready.

`connector-cve` now falls back to a non-empty placeholder API key when `CVE_API_KEY` is left blank, so the container can still start and stay up during normal stack startup. A real NVD API key is still required for successful vulnerability data retrieval; without one, the connector remains running but logs API-key validation errors from NVD.

`tests/test_architecture_connector_support.py` now upgrades `MISP Intel` beyond static configuration checks. The test auto-creates or reuses an OpenCTI live stream, starts a local MISP dependency stack from `docker-compose.misp-test.yml`, bootstraps a valid MISP auth key, and then verifies that `connector-misp-intel` reaches a real running state against that local target.

Architecture and deployment consistency is validated by the pytest suite in `tests/test_architecture_connector_support.py`.

## Data Backup

Use `scripts/backup-opencti.ps1` to create a timestamped backup of the Compose-managed Docker volumes plus the local deployment files.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1
```

The script will:

- detect whether the stack is currently running;
- stop it with `docker compose stop` for a consistent snapshot without deleting data;
- export every Docker volume created by the current Compose project into `backups/<timestamp>/volumes/*.tar.gz`;
- copy `.env`, `docker-compose.yml`, `docker-compose.opensearch.yml`, `docker-compose.misp-test.yml`, `Caddyfile`, and `rabbitmq.conf` into the same backup set;
- restart the stack if it was running before the backup started.

## Safe Stop And Restart

Use `scripts/opencti-stack.ps1` for no-data-loss lifecycle operations.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Stop
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Start
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Restart
```

These commands use `docker compose stop`, `docker compose start`, and `docker compose restart`. They do not remove named volumes, so persisted OpenCTI data remains intact.

If you need to recreate containers without deleting data, use:

```powershell
docker compose down
docker compose up -d
```

Do not add `-v` unless you explicitly want Docker to delete the persisted volumes.

## Backup Dry Run

To preview the backup steps without changing anything:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1 -WhatIf
```

## Community

### Status & bugs

Currently OpenCTI is under heavy development, if you wish to report bugs or ask for new features, you can directly use the [Github issues module](https://github.com/OpenCTI-Platform/opencti/issues).
ss
### Discussion

If you need support or you wish to engage a discussion about the OpenCTI platform, feel free to join us on our [Slack channel](https://community.filigran.io). You can also send us an email to contact@opencti.io.

## About

OpenCTI is a product designed and developed by the company [Filigran](https://filigran.io).

<a href="https://filigran.io" alt="Filigran"><img src="https://github.com/OpenCTI-Platform/opencti/raw/master/.github/img/logo_filigran.png" width="300" /></a>