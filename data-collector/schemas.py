"""Pydantic schemas for Data Collector API."""

import enum
from datetime import datetime

from pydantic import BaseModel


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
