from __future__ import annotations

import os

import pytest

from _fixture_support import ensure_mirror_seed_fixture


@pytest.fixture(scope="module")
def prepared_mirror_seed() -> dict[str, str]:
    ipv4_value = os.getenv("MIRROR_EXPECTED_IPV4_VALUE", "1.2.3.4")
    malware_name = os.getenv("MIRROR_EXPECTED_MALWARE_NAME", "Mirai-Botnet")
    return ensure_mirror_seed_fixture(ipv4_value=ipv4_value, malware_name=malware_name)