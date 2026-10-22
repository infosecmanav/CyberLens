import pytest

from app.intelligence.normalization import NormalizationError, normalize_entity
from app.models.enums import EntityType


@pytest.mark.parametrize(
    ("value", "entity_type", "normalized"),
    [
        ("203.0.113.10", EntityType.IPV4, "203.0.113.10"),
        ("2001:0db8::1", EntityType.IPV6, "2001:db8::1"),
        ("Example.COM.", EntityType.DOMAIN, "example.com"),
        ("HTTPS://Example.COM:443/path#fragment", EntityType.URL, "https://example.com/path"),
        ("A" * 32, EntityType.MD5, "a" * 32),
        ("b" * 40, EntityType.SHA1, "b" * 40),
        ("C" * 64, EntityType.SHA256, "c" * 64),
        ("Analyst@Example.COM", EntityType.EMAIL, "analyst@example.com"),
        ("cve-2021-44228", EntityType.CVE, "CVE-2021-44228"),
        ("as 00123", EntityType.ASN, "AS123"),
        ("192.0.2.9/24", EntityType.NETWORK_RANGE, "192.0.2.0/24"),
        ("t1059.001", EntityType.ATTACK_TECHNIQUE, "T1059.001"),
    ],
)
def test_normalizes_supported_entities(
    value: str, entity_type: EntityType, normalized: str
) -> None:
    result = normalize_entity(value, entity_type)
    assert result.entity_type == entity_type
    assert result.normalized_value == normalized


def test_auto_detects_common_indicator_types() -> None:
    assert normalize_entity("CVE-2024-12345").entity_type == EntityType.CVE
    assert normalize_entity("example.test").entity_type == EntityType.DOMAIN
    assert normalize_entity("https://example.test/a").entity_type == EntityType.URL


@pytest.mark.parametrize(
    "value",
    ["", "not an indicator", "ftp://example.com/file", "https://user:secret@example.com"],
)
def test_rejects_invalid_or_unsafe_values(value: str) -> None:
    with pytest.raises(NormalizationError):
        normalize_entity(value)
