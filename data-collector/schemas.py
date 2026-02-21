"""Pydantic schemas for Data Collector API."""

import enum
import ipaddress
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


class CollectionCreateRequest(BaseModel):
    url: str | None = None
    source_type: SourceType = SourceType.WEB
    options: dict = {}

    @field_validator("url")
    @classmethod
    def validate_url_not_private(cls, v: str | None) -> str | None:
        """Prevent SSRF by blocking private/internal IPs."""
        if v is None:
            return v

        try:
            parsed = urlparse(v)
            hostname = parsed.hostname

            if not hostname:
                return v

            # Try to parse as IP address
            try:
                ip = ipaddress.ip_address(hostname)
                # Block private, loopback, link-local, multicast
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
                # If it's a validation error from our check, re-raise
                if "not allowed" in str(e):
                    raise
                # Otherwise it's not a valid IP, which is fine (it's a hostname)
                pass

            # Block known internal hostnames
            BLOCKED_HOSTNAMES = {
                "localhost",
                "metadata.google.internal",
                "metadata.aws.internal",
            }
            BLOCKED_SUFFIXES = (".internal", ".local", ".localhost")

            hostname_lower = hostname.lower()
            if hostname_lower in BLOCKED_HOSTNAMES:
                raise ValueError(f"URL with internal hostname is not allowed: {hostname}")
            if any(hostname_lower.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
                raise ValueError(f"URL with internal hostname is not allowed: {hostname}")

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
