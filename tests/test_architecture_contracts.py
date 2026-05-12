from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CONTRACTS = [
    ROOT / "OVERALL_ARCHITECTURE.md",
    ROOT / "connectors" / "ARCHITECTURE.md",
    ROOT / "connectors" / "automotive-security-timeline" / "ARCHITECTURE.md",
    ROOT / "scripts" / "ARCHITECTURE.md",
    ROOT / "tests" / "ARCHITECTURE.md",
    ROOT / "tests" / "mirror" / "ARCHITECTURE.md",
    ROOT / "tests" / "runtime" / "ARCHITECTURE.md",
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