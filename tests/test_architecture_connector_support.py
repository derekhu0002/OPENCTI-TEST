from __future__ import annotations

import json
import os
import ssl
import subprocess
import time
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_PATH = ROOT / "design" / "KG" / "SystemArchitecture.json"
ENV_PATH = ROOT / ".env"
MISP_TEST_COMPOSE_PATH = ROOT / "docker-compose.misp-test.yml"
MISP_TEST_ADMIN_KEY = "2a75b4f0c6014f4f9af7f2a1b6e6d7a9b8c4d2e1"
MISP_TEST_ADMIN_EMAIL = "admin@admin.test"
MISP_TEST_BASE_URL = "http://misp-core"
MISP_TEST_STREAM_NAME = "Copilot MISP Intel Runtime"
COMPOSE_FILES = {
    "docker-compose.yml": ROOT / "docker-compose.yml",
    "docker-compose.opensearch.yml": ROOT / "docker-compose.opensearch.yml",
}

CONNECTOR_SPECS = {
    "mitre": {
        "element_id": "1234",
        "element_name": "MITRE ATT&CK",
        "testcase_name": "MITRE ATT&CK数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_mitre_attack_connector_definition",
        "service": "connector-mitre",
        "images": {
            "docker-compose.yml": "opencti/connector-mitre:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-mitre:6.8.17",
        },
        "env_vars": [
            "CONNECTOR_MITRE_ID",
            "MITRE_INTERVAL",
            "MITRE_REMOVE_STATEMENT_MARKING",
        ],
        "compose_refs": [
            "OPENCTI_URL=http://opencti:8080",
            "OPENCTI_TOKEN=${OPENCTI_ADMIN_TOKEN}",
            "CONNECTOR_SCOPE=mitre",
        ],
        "runtime_markers": [
            "Starting PingAlive thread",
        ],
        "runtime_markers_any": [
            "Connector successfully run",
            "Connector registered with ID",
        ],
    },
    "cve": {
        "element_id": "1235",
        "element_name": "NIST NVD CVE",
        "testcase_name": "NIST NVD CVE数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_nist_nvd_cve_connector_definition",
        "service": "connector-cve",
        "images": {
            "docker-compose.yml": "opencti/connector-cve:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-cve:6.8.17",
        },
        "env_vars": ["CONNECTOR_CVE_ID", "CVE_INTERVAL", "CVE_API_KEY"],
        "compose_refs": [
            "CONNECTOR_SCOPE=vulnerability",
            "CVE_API_KEY=${CVE_API_KEY:-runtime-placeholder-key}",
            "profiles: [\"threat-intel-connectors\"]",
        ],
        "runtime_markers": [
            "Starting PingAlive thread",
            "[CONNECTOR] Fetching datasets...",
        ],
        "runtime_markers_any": [
            "Connector registered with ID",
            "New work",
        ],
    },
    "gti": {
        "element_id": "1236",
        "element_name": "Google Threat Intelligence (GTI)",
        "testcase_name": "Google Threat Intelligence (GTI)数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_google_threat_intelligence_connector_definition",
        "service": "connector-google-ti-feeds",
        "images": {
            "docker-compose.yml": "opencti/connector-google-ti-feeds:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-google-ti-feeds:6.8.17",
        },
        "env_vars": [
            "CONNECTOR_GOOGLE_TI_FEEDS_ID",
            "GOOGLE_TI_FEEDS_INTERVAL",
            "GOOGLE_TI_FEEDS_API_KEY",
        ],
        "compose_refs": [
            "CONNECTOR_SCOPE=google-ti-feeds",
            "profiles: [\"threat-intel-connectors\"]",
        ],
    },
    "crowdstrike": {
        "element_id": "1237",
        "element_name": "CrowdStrike Falcon Intelligence",
        "testcase_name": "CrowdStrike Falcon Intelligence数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_crowdstrike_connector_definition",
        "service": "connector-crowdstrike",
        "images": {
            "docker-compose.yml": "opencti/connector-crowdstrike:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-crowdstrike:6.8.17",
        },
        "env_vars": [
            "CONNECTOR_CROWDSTRIKE_ID",
            "CROWDSTRIKE_FALCON_INTERVAL",
            "CROWDSTRIKE_FALCON_BASE_URL",
            "CROWDSTRIKE_FALCON_CLIENT_ID",
            "CROWDSTRIKE_FALCON_CLIENT_SECRET",
        ],
        "compose_refs": [
            "CONNECTOR_SCOPE=crowdstrike",
            "profiles: [\"threat-intel-connectors\"]",
        ],
    },
    "ransomwarelive": {
        "element_id": "1238",
        "element_name": "Ransomware.live",
        "testcase_name": "Ransomware.live数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_ransomwarelive_connector_definition",
        "service": "connector-ransomwarelive",
        "images": {
            "docker-compose.yml": "opencti/connector-ransomwarelive:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-ransomwarelive:6.8.17",
        },
        "env_vars": ["CONNECTOR_RANSOMWARELIVE_ID", "RANSOMWARELIVE_INTERVAL"],
        "compose_refs": [
            "CONNECTOR_SCOPE=ransomwarelive",
            "profiles: [\"threat-intel-connectors\"]",
        ],
        "runtime_markers": [
            "Connector successfully run",
            "404 Client Error: NOT FOUND for url: https://www.ransomware.live/v2/groups",
        ],
    },
    "cisa_kev": {
        "element_id": "1239",
        "element_name": "CISA Known Exploited Vulnerabilities (KEV)",
        "testcase_name": "CISA Known Exploited Vulnerabilities (KEV)数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_cisa_kev_connector_definition",
        "service": "connector-cisa-known-exploited-vulnerabilities",
        "images": {
            "docker-compose.yml": "opencti/connector-cisa-known-exploited-vulnerabilities:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-cisa-known-exploited-vulnerabilities:6.8.17",
        },
        "env_vars": ["CONNECTOR_CISA_KEV_ID", "CISA_KEV_INTERVAL"],
        "compose_refs": [
            "CONNECTOR_SCOPE=cisa-known-exploited-vulnerabilities",
            "profiles: [\"threat-intel-connectors\"]",
        ],
        "runtime_markers": [
            "CISA Bundle Complete",
            "sending bundle to queue",
        ],
    },
    "mandiant": {
        "element_id": "1240",
        "element_name": "Mandiant",
        "testcase_name": "Mandiant数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_mandiant_connector_definition",
        "service": "connector-mandiant",
        "images": {
            "docker-compose.yml": "opencti/connector-mandiant:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-mandiant:6.8.17",
        },
        "env_vars": [
            "CONNECTOR_MANDIANT_ID",
            "MANDIANT_IMPORT_INTERVAL",
            "MANDIANT_API_V4_KEY_ID",
            "MANDIANT_API_V4_KEY_SECRET",
        ],
        "compose_refs": [
            "CONNECTOR_SCOPE=mandiant",
            "profiles: [\"threat-intel-connectors\"]",
        ],
    },
    "threatfox": {
        "element_id": "1241",
        "element_name": "ThreatFox",
        "testcase_name": "ThreatFox数据接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_threatfox_connector_definition",
        "service": "connector-threatfox",
        "images": {
            "docker-compose.yml": "opencti/connector-threatfox:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-threatfox:6.8.17",
        },
        "env_vars": ["CONNECTOR_THREATFOX_ID", "THREATFOX_INTERVAL"],
        "compose_refs": [
            "CONNECTOR_SCOPE=threatfox",
            "profiles: [\"threat-intel-connectors\"]",
        ],
        "runtime_markers": [
            "Connector last run:",
            "Connector will not run, next run in:",
        ],
    },
    "misp_intel": {
        "element_id": "1244",
        "element_name": "MISP Intel",
        "testcase_name": "MISP Intel接入",
        "acceptance": "tests/test_architecture_connector_support.py::test_misp_intel_connector_definition",
        "service": "connector-misp-intel",
        "profile_args": ["--profile", "misp-intel"],
        "images": {
            "docker-compose.yml": "opencti/connector-misp-intel:6.9.0",
            "docker-compose.opensearch.yml": "opencti/connector-misp-intel:6.8.17",
        },
        "env_vars": [
            "CONNECTOR_MISP_INTEL_ID",
            "CONNECTOR_MISP_INTEL_LIVE_STREAM_ID",
            "MISP_URL",
            "MISP_API_KEY",
            "MISP_SSL_VERIFY",
            "MISP_DISTRIBUTION_LEVEL",
            "MISP_THREAT_LEVEL",
            "MISP_OWNER_ORG",
        ],
        "compose_refs": [
            "CONNECTOR_TYPE=STREAM",
            "CONNECTOR_SCOPE=misp",
            "CONNECTOR_LIVE_STREAM_ID=${CONNECTOR_MISP_INTEL_LIVE_STREAM_ID}",
            "profiles: [\"misp-intel\"]",
        ],
        "runtime_markers": [
            "Successfully connected to MISP",
            "MISP Intel connector initialized",
            "Starting MISP Intel connector with worker thread...",
        ],
    },
}
DOCKER_PROFILE_ARGS = ["--profile", "threat-intel-connectors"]


def _load_architecture() -> dict:
    return json.loads(ARCHITECTURE_PATH.read_text(encoding="utf-8"))


def _load_env_lines() -> list[str]:
    return ENV_PATH.read_text(encoding="utf-8").splitlines()


def _load_env_vars() -> dict[str, str]:
    env_vars: dict[str, str] = {}
    for line in _load_env_lines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_vars[key] = value
    return env_vars


def _load_compose_texts() -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8") for name, path in COMPOSE_FILES.items()}


def _run_command(
    args: list[str],
    check: bool = True,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if check and result.returncode != 0:
        command = " ".join(args)
        raise AssertionError(
            f"Command failed: {command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _compose(
    args: list[str],
    check: bool = True,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
    profile_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    compose_args = ["docker", "compose", "-f", str(ROOT / "docker-compose.yml")]
    for compose_file in extra_files or []:
        compose_args.extend(["-f", str(compose_file)])
    compose_args.extend(profile_args or DOCKER_PROFILE_ARGS)
    return _run_command(compose_args + args, check=check, env_overrides=env_overrides)


def _docker_inspect(container_id: str, format_string: str) -> str:
    return _run_command(["docker", "inspect", "-f", format_string, container_id]).stdout.strip()


def _compose_logs(
    service: str,
    *,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
    profile_args: list[str] | None = None,
) -> str:
    result = _compose(
        ["logs", "--tail", "200", service],
        check=False,
        extra_files=extra_files,
        env_overrides=env_overrides,
        profile_args=profile_args,
    )
    return (result.stdout + result.stderr).strip()


def _profile_args_for_spec(spec: dict) -> list[str]:
    return spec.get("profile_args", DOCKER_PROFILE_ARGS)


def _query_misp_user_emails(
    *,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> list[str]:
    result = _compose(
        [
            "exec",
            "-T",
            "misp-db",
            "sh",
            "-lc",
            (
                'mariadb -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" '
                '-Nse "SELECT email FROM users ORDER BY id;"'
            ),
        ],
        check=False,
        extra_files=extra_files,
        env_overrides=env_overrides,
    )
    output = (result.stdout + result.stderr).splitlines()
    return [line.strip() for line in output if "@" in line]


def _configure_misp_authkey(
    *,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> None:
    candidate_emails: list[str] = []
    if env_overrides and env_overrides.get("MISP_TEST_ADMIN_EMAIL"):
        candidate_emails.append(env_overrides["MISP_TEST_ADMIN_EMAIL"])
    candidate_emails.append(MISP_TEST_ADMIN_EMAIL)
    candidate_emails.extend(_query_misp_user_emails(extra_files=extra_files, env_overrides=env_overrides))

    attempted: list[str] = []
    seen: set[str] = set()
    for email in candidate_emails:
        if not email or email in seen:
            continue
        seen.add(email)
        attempted.append(email)
        result = _compose(
            [
                "exec",
                "-T",
                "misp-core",
                "bash",
                "-lc",
                (
                    "cd /var/www/MISP/app && "
                    f"./Console/cake user change_authkey {email} {MISP_TEST_ADMIN_KEY}"
                ),
            ],
            check=False,
            extra_files=extra_files,
            env_overrides=env_overrides,
        )
        if result.returncode == 0:
            return

    raise AssertionError(
        "Unable to configure MISP admin authkey. "
        f"Attempted emails: {attempted or ['<none>']}"
    )


def _graphql_request(query: str) -> dict:
    env_vars = _load_env_vars()
    payload = json.dumps({"query": query}).encode("utf-8")
    graphql_url = f"{env_vars['OPENCTI_BASE_URL']}/graphql"
    headers = {
        "Authorization": f"Bearer {env_vars['OPENCTI_ADMIN_TOKEN']}",
        "Content-Type": "application/json",
    }
    req = request.Request(graphql_url, data=payload, headers=headers, method="POST")
    ssl_context = ssl._create_unverified_context() if graphql_url.startswith("https://") else None

    try:
        with request.urlopen(req, timeout=30, context=ssl_context) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise AssertionError(f"GraphQL request failed: {exc}") from exc

    if "errors" in body:
        raise AssertionError(f"GraphQL returned errors: {body['errors']}")
    return body["data"]


def _ensure_misp_intel_live_stream() -> str:
    streams = _graphql_request("query { streamCollections { edges { node { id name } } } }")
    for edge in streams["streamCollections"]["edges"]:
        node = edge["node"]
        if node["name"] == MISP_TEST_STREAM_NAME:
            return node["id"]

    mutation = (
        "mutation { streamCollectionAdd(input: {"
        f'name: "{MISP_TEST_STREAM_NAME}", '
        'description: "Created for MISP Intel runtime coverage", '
        "stream_public: false, "
        "stream_live: true"
        '}) { id name } }'
    )
    created = _graphql_request(mutation)
    return created["streamCollectionAdd"]["id"]


def _wait_for_service(
    service: str,
    *,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
    timeout: int = 180,
    required_state: str = "running",
    required_health: str | None = None,
    profile_args: list[str] | None = None,
) -> str:
    deadline = time.time() + timeout
    container_id = ""
    last_state = "missing"
    last_health = "unavailable"

    while time.time() < deadline:
        container_id = _compose(
            ["ps", "-q", service],
            extra_files=extra_files,
            env_overrides=env_overrides,
            profile_args=profile_args,
        ).stdout.strip()
        if container_id:
            last_state = _docker_inspect(container_id, "{{.State.Status}}")
            if required_health is not None:
                last_health = _docker_inspect(
                    container_id,
                    "{{if .State.Health}}{{.State.Health.Status}}{{else}}unavailable{{end}}",
                )
            if last_state == required_state and (
                required_health is None or last_health == required_health
            ):
                return container_id
        time.sleep(2)

    logs = _compose_logs(
        service,
        extra_files=extra_files,
        env_overrides=env_overrides,
        profile_args=profile_args,
    )
    raise AssertionError(
        f"{service} did not reach state={required_state} health={required_health}. "
        f"last_state={last_state} last_health={last_health}.\nlogs:\n{logs}"
    )


def _bootstrap_misp_authkey(
    *,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> None:
    _compose(
        ["up", "-d", "misp-redis", "misp-db", "misp-modules", "misp-core"],
        extra_files=extra_files,
        env_overrides=env_overrides,
    )
    _wait_for_service(
        "misp-core",
        extra_files=extra_files,
        env_overrides=env_overrides,
        timeout=600,
        required_health="healthy",
    )
    _configure_misp_authkey(extra_files=extra_files, env_overrides=env_overrides)


def _architecture_element_by_id(element_id: str) -> dict:
    architecture = _load_architecture()
    for element in architecture["elements"]:
        if element["id"] == element_id:
            return element
    raise AssertionError(f"Architecture element {element_id} is missing")


def _testcase_by_name(element: dict, testcase_name: str) -> dict:
    for testcase in element.get("testcases", []):
        if testcase["name"] == testcase_name:
            return testcase
    raise AssertionError(f"Testcase {testcase_name} is missing for {element['name']}")


def _assert_connector_support(spec_key: str) -> None:
    spec = CONNECTOR_SPECS[spec_key]
    element = _architecture_element_by_id(spec["element_id"])
    testcase = _testcase_by_name(element, spec["testcase_name"])
    env_lines = _load_env_lines()
    compose_texts = _load_compose_texts()

    assert element["name"] == spec["element_name"]
    assert testcase["acceptanceCriteria"] == spec["acceptance"]
    assert testcase["description"].strip()

    for env_var in spec["env_vars"]:
        assert any(line.startswith(f"{env_var}=") for line in env_lines), f"Missing {env_var} in .env"

    for compose_name, expected_image in spec["images"].items():
        compose_text = compose_texts[compose_name]
        assert f"  {spec['service']}:" in compose_text, f"Missing {spec['service']} in {compose_name}"
        assert f"    image: {expected_image}" in compose_text, f"Missing image {expected_image} in {compose_name}"
        for marker in spec["compose_refs"]:
            assert marker in compose_text, f"Missing {marker} in {compose_name}"


def _assert_real_container_coverage(
    spec_key: str,
    *,
    extra_files: list[Path] | None = None,
    env_overrides: dict[str, str] | None = None,
    startup_services: list[str] | None = None,
    startup_timeout: int = 180,
) -> None:
    spec = CONNECTOR_SPECS[spec_key]
    service = spec["service"]
    profile_args = _profile_args_for_spec(spec)
    runtime_env = dict(spec.get("runtime_env_overrides", {}))
    if env_overrides:
        runtime_env.update(env_overrides)
    _compose(
        ["up", "-d", *(startup_services or [service])],
        extra_files=extra_files,
        env_overrides=runtime_env or None,
        profile_args=profile_args,
    )

    deadline = time.time() + startup_timeout
    last_status = "missing"
    container_id = ""
    while time.time() < deadline:
        container_id = _compose(
            ["ps", "-q", service],
            extra_files=extra_files,
            env_overrides=runtime_env or None,
            profile_args=profile_args,
        ).stdout.strip()
        if container_id:
            last_status = _docker_inspect(container_id, "{{.State.Status}}")
            if last_status == "running":
                break
        time.sleep(2)

    logs = ""
    log_deadline = time.time() + 120
    while time.time() < log_deadline:
        logs = _compose_logs(
            service,
            extra_files=extra_files,
            env_overrides=runtime_env or None,
            profile_args=profile_args,
        )
        if logs and all(marker in logs for marker in spec.get("runtime_markers", [])):
            break
        time.sleep(2)

    assert container_id, f"No container was created for {service}.\nlogs:\n{logs}"
    assert last_status == "running", f"{service} is not running: {last_status}.\nlogs:\n{logs}"
    assert logs, f"No logs captured for {service}"

    for marker in spec.get("runtime_markers", []):
        assert marker in logs, f"Missing runtime marker '{marker}' for {service}.\nlogs:\n{logs}"
    if spec.get("runtime_markers_any"):
        assert any(marker in logs for marker in spec["runtime_markers_any"]), (
            f"Missing any runtime marker from {spec['runtime_markers_any']} for {service}.\nlogs:\n{logs}"
        )


def test_mitre_attack_connector_definition() -> None:
    _assert_connector_support("mitre")
    _assert_real_container_coverage("mitre")


def test_nist_nvd_cve_connector_definition() -> None:
    _assert_connector_support("cve")
    _assert_real_container_coverage("cve")


def test_google_threat_intelligence_connector_definition() -> None:
    _assert_connector_support("gti")


def test_crowdstrike_connector_definition() -> None:
    _assert_connector_support("crowdstrike")


def test_ransomwarelive_connector_definition() -> None:
    _assert_connector_support("ransomwarelive")
    _assert_real_container_coverage("ransomwarelive")


def test_cisa_kev_connector_definition() -> None:
    _assert_connector_support("cisa_kev")
    _assert_real_container_coverage("cisa_kev")


def test_mandiant_connector_definition() -> None:
    _assert_connector_support("mandiant")


def test_threatfox_connector_definition() -> None:
    _assert_connector_support("threatfox")
    _assert_real_container_coverage("threatfox")


def test_misp_intel_connector_definition() -> None:
    _assert_connector_support("misp_intel")
    stream_id = _ensure_misp_intel_live_stream()
    runtime_env = {
        "CONNECTOR_MISP_INTEL_LIVE_STREAM_ID": stream_id,
        "MISP_API_KEY": MISP_TEST_ADMIN_KEY,
        "MISP_SSL_VERIFY": "false",
        "MISP_TEST_ADMIN_KEY": MISP_TEST_ADMIN_KEY,
        "MISP_TEST_ADMIN_EMAIL": MISP_TEST_ADMIN_EMAIL,
        "MISP_TEST_BASE_URL": MISP_TEST_BASE_URL,
        "MISP_URL": MISP_TEST_BASE_URL,
    }
    _bootstrap_misp_authkey(extra_files=[MISP_TEST_COMPOSE_PATH], env_overrides=runtime_env)
    _assert_real_container_coverage(
        "misp_intel",
        extra_files=[MISP_TEST_COMPOSE_PATH],
        env_overrides=runtime_env,
        startup_timeout=600,
    )


def test_full_architecture_graph_consistency() -> None:
    architecture = _load_architecture()
    all_ids = {element["id"] for element in architecture["elements"]}

    assert len(all_ids) == len(architecture["elements"])

    for view in architecture["views"]:
        for element_id in view.get("included_elements", []):
            assert element_id in all_ids, f"View {view['view_name']} references missing element {element_id}"

    testcase_count = 0
    for element in architecture["elements"]:
        if element.get("type") == "ArchiMate_Principle":
            raise AssertionError("Unexpected ArchiMate_Principle found; add explicit coverage before changing this test")

        for testcase in element.get("testcases", []):
            testcase_count += 1
            assert testcase["name"].strip()
            assert testcase["description"].strip()
            assert testcase["acceptanceCriteria"].strip()
            acceptance = testcase["acceptanceCriteria"]
            file_part = acceptance.split("::", 1)[0]
            target_file = ROOT / file_part
            assert target_file.exists(), f"Acceptance target file is missing: {file_part}"
