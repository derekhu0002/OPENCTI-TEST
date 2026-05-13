from __future__ import annotations

import os


def test_mirror_auto_seed_support_returns_expected_fixture_shape(prepared_mirror_seed: dict[str, str]) -> None:
    assert prepared_mirror_seed["ipv4_value"] == os.getenv("MIRROR_EXPECTED_IPV4_VALUE", "1.2.3.4")
    assert prepared_mirror_seed["malware_name"] == os.getenv("MIRROR_EXPECTED_MALWARE_NAME", "Mirai-Botnet")
    assert prepared_mirror_seed["ipv4_standard_id"]
    assert prepared_mirror_seed["relationship_type"] == "indicates"