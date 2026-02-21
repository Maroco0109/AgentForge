"""Data Collector microservice entry point."""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status

from .collectors.web_crawler import WebCrawler
from .compliance.pii_detector import pii_detector  # noqa: F401
from .compliance.rate_limiter import site_rate_limiter  # noqa: F401
from .compliance.robots_checker import robots_checker
from .processing.anonymizer import anonymizer
from .processing.chunker import text_chunker
from .processing.cleaner import text_cleaner
from .schemas import (
    CollectionCreateRequest,
    CollectionDataResponse,
    CollectionStatus,
    CollectionStatusResponse,
    ComplianceResult,
    ComplianceStatus,
    SourceType,
)

app = FastAPI(
    title="AgentForge Data Collector",
    version="0.1.0",
    description="Data collection microservice with compliance verification",
)

# In-memory storage (will be replaced with DB in Phase 7)
_collections: dict[str, dict] = {}


@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "service": "data-collector", "version": "0.1.0"}


@app.post("/api/v1/collections", status_code=status.HTTP_201_CREATED)
async def create_collection(request: CollectionCreateRequest) -> CollectionStatusResponse:
    """Create a new data collection task."""
    collection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    collection = {
        "id": collection_id,
        "status": CollectionStatus.PENDING,
        "source_type": request.source_type,
        "url": request.url,
        "options": request.options,
        "created_at": now,
        "compliance": None,
        "data": [],
        "error": None,
    }

    _collections[collection_id] = collection

    return CollectionStatusResponse(
        id=collection_id,
        status=CollectionStatus.PENDING,
        source_type=request.source_type,
        url=request.url,
        created_at=now,
    )


@app.get("/api/v1/collections/{collection_id}/compliance")
async def check_compliance(collection_id: str) -> ComplianceResult:
    """Check compliance for a collection."""
    if collection_id not in _collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection = _collections[collection_id]
    collection["status"] = CollectionStatus.CHECKING_COMPLIANCE

    url = collection.get("url")
    if not url:
        result = ComplianceResult(status=ComplianceStatus.ALLOWED, robots_reason="No URL to check")
        collection["compliance"] = result
        return result

    # Check robots.txt
    robots_allowed, robots_reason = await robots_checker.is_allowed(url)

    if not robots_allowed:
        result = ComplianceResult(
            status=ComplianceStatus.BLOCKED,
            robots_allowed=False,
            robots_reason=robots_reason,
        )
        collection["compliance"] = result
        collection["status"] = CollectionStatus.BLOCKED
        return result

    # Check crawl delay
    crawl_delay = await robots_checker.get_crawl_delay(url)
    rate_limit = crawl_delay if crawl_delay else 2.0

    result = ComplianceResult(
        status=ComplianceStatus.ALLOWED,
        robots_allowed=True,
        robots_reason=robots_reason,
        rate_limit_seconds=rate_limit,
    )

    collection["compliance"] = result
    return result


@app.get("/api/v1/collections/{collection_id}/status")
async def get_collection_status(collection_id: str) -> CollectionStatusResponse:
    """Get collection task status."""
    if collection_id not in _collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    c = _collections[collection_id]
    return CollectionStatusResponse(
        id=c["id"],
        status=c["status"],
        source_type=c["source_type"],
        url=c["url"],
        created_at=c["created_at"],
        compliance=c.get("compliance"),
        error=c.get("error"),
    )


@app.post("/api/v1/collections/{collection_id}/collect")
async def run_collection(collection_id: str) -> CollectionStatusResponse:
    """Execute the data collection."""
    if collection_id not in _collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection = _collections[collection_id]

    # Check compliance first
    if collection.get("compliance") is None:
        raise HTTPException(status_code=400, detail="Run compliance check first")

    compliance = collection["compliance"]
    if isinstance(compliance, ComplianceResult) and compliance.status == ComplianceStatus.BLOCKED:
        raise HTTPException(status_code=403, detail="Collection blocked by compliance check")

    collection["status"] = CollectionStatus.COLLECTING

    try:
        url = collection.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        # Crawl
        crawler = WebCrawler()
        result = await crawler.crawl(url)

        if not result.success:
            collection["status"] = CollectionStatus.FAILED
            collection["error"] = result.error
            return CollectionStatusResponse(
                id=collection["id"],
                status=CollectionStatus.FAILED,
                source_type=collection["source_type"],
                url=url,
                created_at=collection["created_at"],
                error=result.error,
            )

        # Process: clean
        collection["status"] = CollectionStatus.PROCESSING
        cleaned_text = text_cleaner.clean(result.text_content)

        # Process: PII check and anonymize
        anonymized_text, pii_result = anonymizer.anonymize(cleaned_text)

        # Process: chunk
        chunks = text_chunker.chunk(anonymized_text, metadata={"url": url, "title": result.title})

        # Store results
        collection["data"] = [
            {"content": chunk.content, "index": chunk.index, "metadata": chunk.metadata}
            for chunk in chunks
        ]
        collection["status"] = CollectionStatus.COMPLETED

        # Update compliance with PII info
        if compliance and isinstance(compliance, ComplianceResult):
            compliance.has_pii = pii_result.has_pii
            compliance.pii_types = list(pii_result.pii_types)

        return CollectionStatusResponse(
            id=collection["id"],
            status=CollectionStatus.COMPLETED,
            source_type=collection["source_type"],
            url=url,
            created_at=collection["created_at"],
            compliance=compliance if isinstance(compliance, ComplianceResult) else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        collection["status"] = CollectionStatus.FAILED
        collection["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/collections/{collection_id}/data")
async def get_collection_data(collection_id: str) -> CollectionDataResponse:
    """Get collected and processed data."""
    if collection_id not in _collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    c = _collections[collection_id]
    return CollectionDataResponse(
        id=c["id"],
        status=c["status"],
        data=c.get("data", []),
        total_items=len(c.get("data", [])),
        metadata={
            "url": c.get("url"),
            "source_type": (
                c["source_type"].value
                if isinstance(c["source_type"], SourceType)
                else c["source_type"]
            ),
        },
    )
