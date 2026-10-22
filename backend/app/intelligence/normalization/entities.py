import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field

from app.models.enums import EntityType

_CVE = re.compile(r"^CVE-(\d{4})-(\d{4,})$", re.IGNORECASE)
_ASN = re.compile(r"^AS\s*([0-9]{1,10})$", re.IGNORECASE)
_HASHES: tuple[tuple[int, EntityType], ...] = (
    (32, EntityType.MD5),
    (40, EntityType.SHA1),
    (64, EntityType.SHA256),
)
_HEX = re.compile(r"^[0-9a-fA-F]+$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+$")
_ATTACK = re.compile(r"^T\d{4}(?:\.\d{3})?$", re.IGNORECASE)
_GENERIC_TYPES = {
    EntityType.PRODUCT,
    EntityType.MALWARE_FAMILY,
    EntityType.CAMPAIGN,
    EntityType.THREAT_ACTOR,
}


class NormalizationError(ValueError):
    pass


class NormalizedEntity(BaseModel):
    entity_type: EntityType
    original_value: str
    normalized_value: str
    attributes: dict[str, Any] = Field(default_factory=dict)


def _domain(value: str) -> tuple[str, dict[str, Any]]:
    candidate = value.rstrip(".")
    try:
        normalized = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise NormalizationError("Domain contains invalid internationalized characters") from exc
    if len(normalized) > 253 or "." not in normalized:
        raise NormalizationError("Domain must be a fully qualified name")
    labels = normalized.split(".")
    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or re.fullmatch(r"[a-z0-9-]+", label) is None
        for label in labels
    ):
        raise NormalizationError("Domain contains an invalid label")
    if labels[-1].isdigit():
        raise NormalizationError("Domain suffix cannot be numeric")
    return normalized, {"unicode_value": candidate if normalized != candidate.lower() else None}


def _ip(value: str) -> tuple[EntityType, str, dict[str, Any]]:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise NormalizationError("Invalid IP address") from exc
    entity_type = EntityType.IPV4 if address.version == 4 else EntityType.IPV6
    return entity_type, address.compressed, {
        "version": address.version,
        "is_private": address.is_private,
        "is_global": address.is_global,
        "is_reserved": address.is_reserved,
    }


def _url(value: str) -> tuple[str, dict[str, Any]]:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise NormalizationError("URL is malformed") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or parsed.hostname is None:
        raise NormalizationError("URL must use http or https and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise NormalizationError("URLs containing credentials are not accepted")
    host = parsed.hostname
    host_attributes: dict[str, Any]
    try:
        address_type, normalized_host, host_attributes = _ip(host)
        host_attributes["host_entity_type"] = address_type.value
        display_host = (
            f"[{normalized_host}]" if address_type == EntityType.IPV6 else normalized_host
        )
    except NormalizationError:
        normalized_host, host_attributes = _domain(host)
        host_attributes["host_entity_type"] = EntityType.DOMAIN.value
        display_host = normalized_host
    if port is not None and not (1 <= port <= 65535):
        raise NormalizationError("URL port is outside the valid range")
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = display_host if port is None or default_port else f"{display_host}:{port}"
    path = parsed.path or "/"
    normalized = urlunsplit((scheme, netloc, path, parsed.query, ""))
    return normalized, {"scheme": scheme, "host": normalized_host, "port": port, **host_attributes}


def _certificate(value: str) -> tuple[str, dict[str, Any]]:
    fingerprint = value.replace(":", "").replace(" ", "").lower()
    if len(fingerprint) not in {40, 64} or _HEX.fullmatch(fingerprint) is None:
        raise NormalizationError("Certificate must be a SHA-1 or SHA-256 fingerprint")
    return fingerprint, {"fingerprint_algorithm": "SHA1" if len(fingerprint) == 40 else "SHA256"}


def _explicit(value: str, entity_type: EntityType) -> tuple[str, dict[str, Any]]:
    if entity_type in {EntityType.IPV4, EntityType.IPV6}:
        detected, normalized, attributes = _ip(value)
        if detected != entity_type:
            raise NormalizationError(f"Value is {detected.value}, not {entity_type.value}")
        return normalized, attributes
    if entity_type == EntityType.DOMAIN:
        return _domain(value)
    if entity_type == EntityType.URL:
        return _url(value)
    if entity_type in {EntityType.MD5, EntityType.SHA1, EntityType.SHA256}:
        lengths = {EntityType.MD5: 32, EntityType.SHA1: 40, EntityType.SHA256: 64}
        if len(value) != lengths[entity_type] or _HEX.fullmatch(value) is None:
            raise NormalizationError(f"Value is not a valid {entity_type.value} hash")
        return value.lower(), {"algorithm": entity_type.value}
    if entity_type == EntityType.CVE:
        match = _CVE.fullmatch(value)
        if match is None:
            raise NormalizationError("CVE must use the form CVE-YYYY-NNNN")
        return f"CVE-{match.group(1)}-{match.group(2)}", {}
    if entity_type == EntityType.ASN:
        match = _ASN.fullmatch(value)
        if match is None:
            raise NormalizationError("ASN must use the form AS123")
        number = int(match.group(1))
        if number > 4_294_967_295:
            raise NormalizationError("ASN is outside the valid range")
        return f"AS{number}", {"number": number}
    if entity_type == EntityType.EMAIL:
        if _EMAIL.fullmatch(value) is None:
            raise NormalizationError("Email address is malformed")
        local, raw_domain = value.rsplit("@", 1)
        domain, _ = _domain(raw_domain)
        return f"{local.lower()}@{domain}", {"domain": domain}
    if entity_type == EntityType.CERTIFICATE:
        return _certificate(value)
    if entity_type == EntityType.NAMESERVER:
        return _domain(value)
    if entity_type == EntityType.NETWORK_RANGE:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise NormalizationError("Network range must be valid CIDR notation") from exc
        return network.compressed, {"version": network.version, "prefix_length": network.prefixlen}
    if entity_type == EntityType.ATTACK_TECHNIQUE:
        if _ATTACK.fullmatch(value) is None:
            raise NormalizationError("ATT&CK technique must use T1234 or T1234.001")
        return value.upper(), {}
    if entity_type in _GENERIC_TYPES:
        normalized = " ".join(value.split()).casefold()
        if len(normalized) < 2:
            raise NormalizationError("Entity value is too short")
        return normalized, {}
    raise NormalizationError(f"Normalization is not implemented for {entity_type.value}")


def normalize_entity(value: str, entity_type: EntityType | None = None) -> NormalizedEntity:
    original = value
    candidate = value.strip()
    if not candidate:
        raise NormalizationError("Entity value cannot be empty")
    if len(candidate) > 2048:
        raise NormalizationError("Entity value exceeds 2048 characters")

    if entity_type is not None:
        normalized, attributes = _explicit(candidate, entity_type)
        return NormalizedEntity(
            entity_type=entity_type,
            original_value=original,
            normalized_value=normalized,
            attributes={key: item for key, item in attributes.items() if item is not None},
        )

    for length, hash_type in _HASHES:
        if len(candidate) == length and _HEX.fullmatch(candidate):
            return normalize_entity(candidate, hash_type)
    if _CVE.fullmatch(candidate):
        return normalize_entity(candidate, EntityType.CVE)
    if _ASN.fullmatch(candidate):
        return normalize_entity(candidate, EntityType.ASN)
    if "://" in candidate:
        return normalize_entity(candidate, EntityType.URL)
    if "@" in candidate:
        return normalize_entity(candidate, EntityType.EMAIL)
    try:
        detected_ip, _, _ = _ip(candidate)
        return normalize_entity(candidate, detected_ip)
    except NormalizationError:
        pass
    try:
        _domain(candidate)
        return normalize_entity(candidate, EntityType.DOMAIN)
    except NormalizationError as exc:
        raise NormalizationError(
            "Could not detect the entity type; provide a supported type explicitly"
        ) from exc
