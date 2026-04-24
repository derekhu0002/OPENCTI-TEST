from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_PATH = ROOT / "design" / "KG" / "SystemArchitecture.json"
ENV_PATH = ROOT / ".env"
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
            "Connector successfully run",
            "Reporting work update_processed",
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
            "profiles: [\"threat-intel-connectors\"]",
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
            "Connector successfully run",
            "Last_run stored, next run in:",
        ],
    },
}

PENDING_TESTCASES = {"1244": "MISP Intel接入"}
DOCKER_PROFILE_ARGS = ["docker", "compose", "--profile", "threat-intel-connectors"]


def _load_architecture() -> dict:
    return json.loads(ARCHITECTURE_PATH.read_text(encoding="utf-8"))


def _load_env_lines() -> list[str]:
    return ENV_PATH.read_text(encoding="utf-8").splitlines()


def _load_compose_texts() -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8") for name, path in COMPOSE_FILES.items()}


def _run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if check and result.returncode != 0:
        command = " ".join(args)
        raise AssertionError(
            f"Command failed: {command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _compose(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run_command(DOCKER_PROFILE_ARGS + args, check=check)


def _docker_inspect(container_id: str, format_string: str) -> str:
    return _run_command(["docker", "inspect", "-f", format_string, container_id]).stdout.strip()


def _compose_logs(service: str) -> str:
    result = _compose(["logs", "--tail", "200", service], check=False)
    return (result.stdout + result.stderr).strip()


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


def _assert_real_container_coverage(spec_key: str) -> None:
    spec = CONNECTOR_SPECS[spec_key]
    service = spec["service"]
    _compose(["up", "-d", service])

    deadline = time.time() + 180
    last_status = "missing"
    container_id = ""
    while time.time() < deadline:
        container_id = _compose(["ps", "-q", service]).stdout.strip()
        if container_id:
            last_status = _docker_inspect(container_id, "{{.State.Status}}")
            if last_status == "running":
                break
        time.sleep(2)

    logs = _compose_logs(service)
    assert container_id, f"No container was created for {service}.\nlogs:\n{logs}"
    assert last_status == "running", f"{service} is not running: {last_status}.\nlogs:\n{logs}"
    assert logs, f"No logs captured for {service}"

    for marker in spec.get("runtime_markers", []):
        assert marker in logs, f"Missing runtime marker '{marker}' for {service}.\nlogs:\n{logs}"


def test_mitre_attack_connector_definition() -> None:
    _assert_connector_support("mitre")
    _assert_real_container_coverage("mitre")


def test_nist_nvd_cve_connector_definition() -> None:
    _assert_connector_support("cve")


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


def test_full_architecture_graph_consistency() -> None:
    architecture = _load_architecture()
    all_ids = {element["id"] for element in architecture["elements"]}

    assert len(all_ids) == len(architecture["elements"])

    for view in architecture["views"]:
        for element_id in view.get("included_elements", []):
            assert element_id in all_ids, f"View {view['view_name']} references missing element {element_id}"

    testcase_count = 0
    pending = []
    for element in architecture["elements"]:
        if element.get("type") == "ArchiMate_Principle":
            raise AssertionError("Unexpected ArchiMate_Principle found; add explicit coverage before changing this test")

        for testcase in element.get("testcases", []):
            testcase_count += 1
            assert testcase["name"].strip()

            if testcase.get("acceptanceCriteria", "").strip():
                assert testcase["description"].strip()
                acceptance = testcase["acceptanceCriteria"]
                file_part = acceptance.split("::", 1)[0]
                target_file = ROOT / file_part
                assert target_file.exists(), f"Acceptance target file is missing: {file_part}"
            else:
                pending.append((element["id"], testcase["name"]))

    assert testcase_count == 9
    assert pending == [("1244", "MISP Intel接入")]
