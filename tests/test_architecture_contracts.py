from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CONTRACTS = [
    ROOT / "OVERALL_ARCHITECTURE.md",
    ROOT / "connectors" / "ARCHITECTURE.md",
    ROOT / "connectors" / "automotive-security-timeline" / "ARCHITECTURE.md",
    ROOT / "mirror-sync" / "ARCHITECTURE.md",
    ROOT / "query-backend" / "ARCHITECTURE.md",
    ROOT / "scripts" / "ARCHITECTURE.md",
    ROOT / "tests" / "ARCHITECTURE.md",
    ROOT / "tests" / "mirror" / "ARCHITECTURE.md",
    ROOT / "tests" / "query_backend" / "ARCHITECTURE.md",
    ROOT / "tests" / "runtime" / "ARCHITECTURE.md",
]

RUNTIME_PLATFORM_FILES = [
    ROOT / "docker-compose.yml",
    ROOT / "mirror-sync" / "Dockerfile",
    ROOT / "mirror-sync" / "service.py",
    ROOT / "query-backend" / "Dockerfile",
]

REQUIRED_HEADINGS = [
    "## 1. 角色",
    "## 2. 作用域",
    "## 3. 稳定元素",
    "## 4. 接口边界",
    "## 5. 依赖方向",
    "## 6. implements 追溯",
    "## 7. 显性 testcase 入口",
    "## 8. 关键非显性测试",
    "## 9. 普通非显性测试",
    "## 10. 保护对象",
    "## 11. 变更规则",
]


def test_required_contract_files_exist() -> None:
    missing = [path for path in REQUIRED_CONTRACTS if not path.is_file()]
    assert not missing, f"Missing architecture contracts: {missing}"


def test_contracts_use_shared_skeleton() -> None:
    for path in REQUIRED_CONTRACTS:
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            assert heading in text, f"{path} missing heading {heading}"


def test_local_contracts_reference_root_contract() -> None:
    root_contract = ROOT / "OVERALL_ARCHITECTURE.md"
    for path in REQUIRED_CONTRACTS:
        if path == root_contract:
            continue
        text = path.read_text(encoding="utf-8")
        assert "OVERALL_ARCHITECTURE.md" in text, f"{path} must reference the root contract"


def test_query_backend_container_delivery_is_physicalized() -> None:
    missing = [path for path in RUNTIME_PLATFORM_FILES if not path.is_file()]
    assert not missing, f"Missing runtime delivery files: {missing}"

    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    mirror_dockerfile_text = (ROOT / "mirror-sync" / "Dockerfile").read_text(encoding="utf-8")
    mirror_service_text = (ROOT / "mirror-sync" / "service.py").read_text(encoding="utf-8")
    dockerfile_text = (ROOT / "query-backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "query-backend:" in compose_text
    assert "dockerfile: query-backend/Dockerfile" in compose_text
    assert "mirror-sync:" in compose_text
    assert "dockerfile: mirror-sync/Dockerfile" in compose_text
    assert "STREAM_ID=${MIRROR_STREAM_ID:-bootstrap-placeholder-stream}" in compose_text
    assert "BOOTSTRAP_START_AT=${BOOTSTRAP_START_AT:-}" in compose_text
    assert "MIRROR_BOOTSTRAP_LOOKBACK_DAYS=${MIRROR_BOOTSTRAP_LOOKBACK_DAYS:-365}" in compose_text
    assert "MIRROR_POLL_INTERVAL_SECONDS=${MIRROR_POLL_INTERVAL_SECONDS:-15}" in compose_text
    assert "${QUERY_BACKEND_PORT:-8088}:8088" in compose_text
    assert "./mirror-sync/runtime" in compose_text
    assert "./query-backend/runtime" in compose_text
    assert "query-backend:8088" in (ROOT / "Caddyfile").read_text(encoding="utf-8")
    assert "FROM python:3.13-slim" in mirror_dockerfile_text
    assert "service.py" in mirror_dockerfile_text
    assert "bootstrap_start_at" in mirror_service_text
    assert "candidate relationship scope templates" in (ROOT / "mirror-sync" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "candidate relationship scope templates" in (ROOT / "OVERALL_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "FROM python:3.13-slim" in dockerfile_text
    assert "server.py" in dockerfile_text