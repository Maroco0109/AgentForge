"""Pydantic schemas for Data Collector API."""

import enum
import ipaddress
import socket
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class CollectionStatus(str, enum.Enum):
    PENDING = "pending"
    CHECKING_COMPLIANCE = "checking_compliance"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class SourceType(str, enum.Enum):
    WEB = "web"
    API = "api"
    PDF = "pdf"
    FILE = "file"


class ComplianceStatus(str, enum.Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    WARNING = "warning"
    UNCHECKED = "unchecked"


BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.aws.internal",
}
BLOCKED_SUFFIXES = (".internal", ".local", ".localhost")


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private/internal."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
        )
    except ValueError:
        return False


class CollectionCreateRequest(BaseModel):
    url: str | None = None
    source_type: SourceType = SourceType.WEB
    options: dict = {}

    @field_validator("url")
    @classmethod
    def validate_url_not_private(cls, v: str | None) -> str | None:
        """Prevent SSRF by blocking private/internal IPs and hostnames."""
        if v is None:
            return v

        try:
            parsed = urlparse(v)
            hostname = parsed.hostname

            if not hostname:
                return v

            # Check literal IP address
            try:
                ip = ipaddress.ip_address(hostname)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                ):
                    raise ValueError(
                        f"URL with private/internal IP address is not allowed: {hostname}"
                    )
            except ValueError as e:
                if "not allowed" in str(e):
                    raise
                # Not a valid IP, it's a hostname - continue checking
                pass

            # Block known internal hostnames
            hostname_lower = hostname.lower()
            if hostname_lower in BLOCKED_HOSTNAMES:
                raise ValueError(f"URL with internal hostname is not allowed: {hostname}")
            if any(hostname_lower.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
                raise ValueError(f"URL with internal hostname is not allowed: {hostname}")

            # DNS resolution check: resolve hostname and verify resolved IPs are not private
            try:
                addrinfo = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
                for family, _type, _proto, _canonname, sockaddr in addrinfo:
                    resolved_ip = sockaddr[0]
                    if _is_private_ip(resolved_ip):
                        raise ValueError(
                            f"URL hostname resolves to private IP: {hostname} -> {resolved_ip}"
                        )
            except socket.gaierror:
                # DNS resolution failed - allow (will fail at request time)
                pass

            return v
        except ValueError:
            raise


class ComplianceResult(BaseModel):
    status: ComplianceStatus = ComplianceStatus.UNCHECKED
    robots_allowed: bool = True
    robots_reason: str = ""
    has_pii: bool = False
    pii_types: list[str] = []
    rate_limit_seconds: float = 2.0


class CollectionStatusResponse(BaseModel):
    id: str
    status: CollectionStatus
    source_type: SourceType
    url: str | None = None
    created_at: datetime
    compliance: ComplianceResult | None = None
    error: str | None = None


class CollectionDataResponse(BaseModel):
    id: str
    status: CollectionStatus
    data: list[dict] = []
    total_items: int = 0
    metadata: dict = {}
