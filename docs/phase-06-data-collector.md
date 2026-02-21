# Phase 6: Data Collector 마이크로서비스

## 개요

Phase 6은 독립적인 마이크로서비스로 동작하는 데이터 수집 시스템입니다. 웹 크롤링, API 데이터 수집, 파일 읽기를 지원하며, robots.txt 준수, 한국어 PII 탐지 및 비식별화, 텍스트 청킹을 포함합니다. Phase 5의 Pipeline Orchestrator와 독립적으로 실행 가능합니다.

**목표:**
- 웹 크롤링, API 수집, 파일 읽기 통합
- robots.txt 파싱 및 크롤링 허용 여부 판단
- 한국어 PII 탐지 (전화번호, 이메일, 주민번호, 카드, 이름, 주소)
- PII 비식별화 (한국어 레이블로 대체)
- 텍스트 정규화 및 청킹 (LLM 처리용)
- 사이트별 속도 제한 (Rate Limiting)
- FastAPI 마이크로서비스 구조

**기술 스택:**
- FastAPI (독립 웹 서비스)
- httpx (async HTTP 클라이언트)
- BeautifulSoup (HTML 파싱)
- pandas (파일 읽기: CSV, Excel, JSON)
- urllib.robotparser (robots.txt 파싱)
- re (정규식 기반 PII 탐지)

## 시스템 아키텍처

```
클라이언트 요청
    ↓
[API Gateway] (FastAPI)
    ├─→ POST /api/v1/collections (수집 작업 생성)
    ├─→ GET /api/v1/collections/{id}/status (상태 조회)
    ├─→ POST /api/v1/collections/{id}/collect (수집 실행)
    └─→ GET /api/v1/collections/{id}/data (데이터 조회)
    ↓
┌──────────────────────────────────────────────────┐
│ Compliance Gateway                               │
├──────────────────────────────────────────────────┤
│ [RobotsChecker] → robots.txt 파싱 및 허용 여부   │
│ [RateLimiter] → 사이트별 요청 속도 제한         │
└──────────────────────────────────────────────────┘
    ↓ (허용된 경우만)
┌──────────────────────────────────────────────────┐
│ Collector Pool                                   │
├──────────────────────────────────────────────────┤
│ [WebCrawler] (httpx + BeautifulSoup)            │
│ [APIFetcher] (httpx async)                      │
│ [FileReader] (pandas)                           │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│ Processing Pipeline                              │
├──────────────────────────────────────────────────┤
│ 1. HTML/Text Cleaner → 정규식 기반 정제         │
│ 2. PII Detector → 한국어 패턴 탐지              │
│ 3. Anonymizer → 한국어 레이블 대체               │
│ 4. Text Chunker → LLM 처리용 분할               │
└──────────────────────────────────────────────────┘
    ↓
응답 (청크된 데이터 + 메타데이터)
```

## Compliance Gateway

### RobotsChecker

robots.txt 준수를 통한 윤리적 크롤링:

```python
class RobotsChecker:
    """robots.txt 파싱 및 준수."""

    async def is_allowed(self, url: str) -> tuple[bool, str]:
        """
        URL 크롤링 허용 여부 확인.

        Returns: (is_allowed, reason)
        """
        # robots.txt 가져오기
        robots_url = f"{scheme}://{netloc}/robots.txt"
        parser = await self._get_parser(robots_url)

        if parser is None:
            return True, "robots.txt not found - assuming allowed"

        # AgentForgeBot 에이전트 확인
        allowed = parser.can_fetch("AgentForgeBot/1.0", url)

        return allowed, reason

    async def get_crawl_delay(self, url: str) -> float | None:
        """robots.txt에서 crawl-delay 추출."""
        # crawl-delay 값 반환 (기본값 2초)
        pass
```

### RateLimiter

사이트별 요청 속도 제한:

```python
class RateLimiter:
    """사이트별 속도 제한."""

    async def wait_if_needed(self, domain: str):
        """필요 시 요청 지연."""
        # domain별 마지막 요청 시간 추적
        # robots.txt crawl-delay만큼 대기
        pass

    async def is_allowed(self, domain: str) -> bool:
        """속도 제한 준수 확인."""
        pass
```

## Collector Pool

### WebCrawler

웹 페이지 크롤링:

```python
class WebCrawler:
    """httpx + BeautifulSoup 기반 웹 크롤러."""

    async def crawl(self, url: str) -> CrawlResult:
        """
        URL 크롤링 및 콘텐츠 추출.

        Returns: CrawlResult(
            url, status_code, title, text_content,
            html_content, links, error, success
        )
        """
        # httpx로 페이지 가져오기
        # BeautifulSoup으로 파싱
        # 스크립트, 스타일, nav, footer, header 제거
        # 텍스트/링크/제목 추출
        pass
```

**CrawlResult:**
```python
@dataclass
class CrawlResult:
    url: str
    status_code: int
    title: str = ""
    text_content: str = ""  # 추출된 텍스트
    html_content: str = ""  # 원본 HTML
    links: list[str] = []   # 발견된 링크 (최대 50개)
    error: str | None = None
    success: bool = True
```

### APIFetcher

구조화된 API에서 데이터 수집:

```python
class APIFetcher:
    """REST API에서 데이터 수집."""

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        params: dict | None = None
    ) -> APIFetchResult:
        """API 요청 및 응답 파싱."""
        # httpx로 API 호출
        # JSON 파싱
        # 메타데이터 추출
        pass
```

### FileReader

로컬/원격 파일 읽기:

```python
class FileReader:
    """CSV, Excel, JSON 파일 읽기."""

    async def read(self, file_path: str) -> FileReadResult:
        """
        파일 읽기 및 구조화.

        지원 형식: .csv, .xlsx, .xls, .json
        """
        # pandas로 파일 로드
        # 데이터프레임 → 텍스트 변환
        # 메타데이터 추출
        pass
```

## Processing Pipeline

### 1. TextCleaner

HTML 및 텍스트 정규화:

```python
class TextCleaner:
    """HTML 제거 및 텍스트 정규화."""

    def clean(self, text: str) -> str:
        """
        - HTML 태그 제거
        - 연속 공백 제거
        - 특수 문자 정규화
        - 줄 바꿈 통일
        - 한글 텍스트 보존
        """
        # re.sub를 통한 정규식 기반 정제
        pass
```

### 2. PIIDetector

한국어 PII 탐지:

```python
class PIIDetector:
    """한국어 PII 탐지."""

    PII_PATTERNS = {
        "phone": [
            r"01[0-9]-?\d{3,4}-?\d{4}",      # 휴대폰
            r"0[2-6][0-9]{0,2}-?\d{3,4}-?\d{4}"  # 유선
        ],
        "email": [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        ],
        "ssn": [
            r"\d{6}-?[1-4]\d{6}"  # 주민등록번호
        ],
        "card_number": [
            r"\d{4}-?\d{4}-?\d{4}-?\d{4}"  # 신용카드
        ],
        "name_pattern": [
            r"[가-힣]{2,4}\s*(?:씨|님|선생|교수|박사)"  # 이름 + 호칭
        ],
        "address": [
            r"[가-힣]+(?:시|도)\s+[가-힣]+(?:구|군|시)"  # 주소
        ]
    }

    def detect(self, text: str) -> PIIDetectionResult:
        """
        PII 탐지 및 위치 기록.

        Returns: PIIDetectionResult(
            found: [{"type": "phone", "value": "010-...", "start": 0, "end": 13}],
            has_pii: bool,
            pii_types: {"phone", "email", ...}
        )
        """
        pass
```

**PIIDetectionResult:**
```python
@dataclass
class PIIDetectionResult:
    found: list[dict]     # [{"type": "phone", "value": "...", "start": 0, "end": 13}]
    has_pii: bool
    pii_types: set[str]   # {"phone", "email", "ssn"}
```

### 3. Anonymizer

PII 비식별화:

```python
class Anonymizer:
    """PII를 한국어 레이블로 대체."""

    REPLACEMENT_MAP = {
        "phone": "[전화번호]",
        "email": "[이메일]",
        "ssn": "[주민번호]",
        "card_number": "[카드번호]",
        "name_pattern": "[이름]",
        "address": "[주소]"
    }

    def anonymize(self, text: str) -> tuple[str, PIIDetectionResult]:
        """
        PII 대체 (뒤에서부터 위치 조정하며 대체).

        Returns: (anonymized_text, detection_result)
        """
        # 위치 역순 정렬 (문자열 길이 변경 때문)
        # 한국어 레이블로 대체
        pass
```

### 4. TextChunker

LLM 처리용 청킹:

```python
class TextChunker:
    """텍스트를 LLM 처리 가능한 청크로 분할."""

    def chunk(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
        metadata: dict | None = None
    ) -> list[TextChunk]:
        """
        겹침을 고려한 청크 분할.

        Returns: [TextChunk(content, index, metadata)]
        """
        # 최대 chunk_size 글자로 분할
        # 겹침(overlap) 적용으로 문맥 유지
        # 한국어 음절 기준 분할 (단어 자르지 않기)
        pass
```

**TextChunk:**
```python
@dataclass
class TextChunk:
    content: str
    index: int
    metadata: dict = None
```

## API 엔드포인트

### 1. 수집 작업 생성

**요청:**
```http
POST /api/v1/collections
Content-Type: application/json

{
  "source_type": "web",
  "url": "https://example.com/article",
  "options": {
    "max_depth": 1,
    "follow_links": false
  }
}
```

**응답 (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "source_type": "web",
  "url": "https://example.com/article",
  "created_at": "2024-02-21T10:30:00Z"
}
```

### 2. Compliance 검사

**요청:**
```http
GET /api/v1/collections/550e8400.../compliance
```

**응답:**
```json
{
  "status": "allowed",
  "robots_allowed": true,
  "robots_reason": "Allowed by robots.txt (crawl-delay: 2.0s)",
  "rate_limit_seconds": 2.0,
  "has_pii": false,
  "pii_types": []
}
```

**차단된 경우:**
```json
{
  "status": "blocked",
  "robots_allowed": false,
  "robots_reason": "Blocked by robots.txt for example.com",
  "rate_limit_seconds": 2.0
}
```

### 3. 수집 실행

**요청:**
```http
POST /api/v1/collections/550e8400.../collect
```

**응답 (200 OK):**
```json
{
  "id": "550e8400...",
  "status": "completed",
  "source_type": "web",
  "url": "https://example.com/article",
  "created_at": "2024-02-21T10:30:00Z",
  "compliance": {
    "status": "allowed",
    "has_pii": true,
    "pii_types": ["phone", "name"]
  }
}
```

### 4. 수집된 데이터 조회

**요청:**
```http
GET /api/v1/collections/550e8400.../data
```

**응답:**
```json
{
  "id": "550e8400...",
  "status": "completed",
  "total_items": 5,
  "data": [
    {
      "content": "첫 번째 청크...",
      "index": 0,
      "metadata": {
        "url": "https://example.com/article",
        "title": "기사 제목"
      }
    },
    {
      "content": "두 번째 청크...",
      "index": 1,
      "metadata": { ... }
    }
  ],
  "metadata": {
    "source_type": "web",
    "url": "https://example.com/article"
  }
}
```

### 5. 수집 상태 조회

**요청:**
```http
GET /api/v1/collections/550e8400.../status
```

**응답:**
```json
{
  "id": "550e8400...",
  "status": "processing",
  "source_type": "web",
  "url": "https://example.com/article",
  "created_at": "2024-02-21T10:30:00Z",
  "error": null
}
```

## 구현 세부사항

### 디렉토리 구조

```
data-collector/
├── main.py                 # FastAPI 애플리케이션
├── config.py               # 설정 (CollectorSettings)
├── schemas.py              # Pydantic 스키마
├── compliance/
│   ├── robots_checker.py   # RobotsChecker
│   ├── rate_limiter.py     # RateLimiter
│   ├── pii_detector.py     # PIIDetector
│   └── __init__.py
├── collectors/
│   ├── web_crawler.py      # WebCrawler
│   ├── api_fetcher.py      # APIFetcher
│   ├── file_reader.py      # FileReader
│   └── __init__.py
├── processing/
│   ├── cleaner.py          # TextCleaner
│   ├── anonymizer.py       # Anonymizer
│   ├── chunker.py          # TextChunker
│   └── __init__.py
├── requirements.txt        # 의존성
└── Dockerfile              # 독립 실행 컨테이너
```

### 설정

```python
# config.py
class CollectorSettings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://..."
    REDIS_URL: str = "redis://localhost:6379"
    DEFAULT_RATE_LIMIT_SECONDS: float = 2.0
    MAX_COLLECTION_SIZE_MB: int = 100
    PII_DETECTION_ENABLED: bool = True
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
```

## 수집 상태 다이어그램

```
pending
    ↓
checking_compliance ←─────────────────┐
    ├─→ blocked (robots 차단)        │
    ├─→ allowed                      │
    │   ↓                            │
    │ collecting                     │
    │   ├─→ failed                   │
    │   ├─→ processing               │
    │   │   ↓                        │
    │   │ completed                  │
    │   └─→ failed                   │
    │       (처리 중 에러)            │
    └──────────────────────────────→ failed
```

## 한국어 PII 탐지 예시

| 타입 | 패턴 | 예시 | 대체 |
|------|------|------|------|
| phone | 01X-XXXX-XXXX | 010-1234-5678 | [전화번호] |
| email | user@example.com | john@email.com | [이메일] |
| ssn | XXXXXX-X000000 | 001122-1000000 | [주민번호] |
| card | XXXX-XXXX-XXXX-XXXX | 1234-5678-9012-3456 | [카드번호] |
| name | 홍길동 님 | 김철수 교수 | [이름] |
| address | 서울시 강남구 역삼동 | 부산시 해운대구 해변로 | [주소] |

## 독립 실행

Phase 5 없이 독립적으로 실행 가능:

```bash
# Docker로 실행
docker build -f docker/Dockerfile.collector -t agentforge-collector .
docker run -p 8001:8000 agentforge-collector

# 또는 Docker Compose
docker-compose up data-collector
```

**API 접속:**
- Health: `http://localhost:8001/api/v1/health`
- API 문서: `http://localhost:8001/docs`

## 성능 고려사항

### 수집 시간 추정

| 소스 | 크기 | 시간 | 비용 |
|------|------|------|------|
| 웹페이지 | 100KB | 2-5초 | 무료 |
| CSV (1MB) | 1MB | 1-2초 | 무료 |
| API (JSON) | 500KB | 1-3초 | API 정책 |

### 동시성

- 최대 동시 수집: 10개 (메모리 제약)
- 큐 대기: 100개
- 타임아웃: 30초

## 보안 고려사항

1. **robots.txt 준수**: 윤리적 크롤링
2. **Rate Limiting**: 서버 부담 완화
3. **PII 탐지/비식별화**: 개인정보 보호
4. **User-Agent**: 투명한 봇 식별
5. **입력 검증**: URL/파일 경로 검증

## 다음 단계

### Phase 7: 메인 플랫폼 통합
- 데이터 수집기를 메인 API와 연동
- 수집 결과를 Discussion Engine에 전달
- 비용 추적 및 청구 시스템

### Phase 8: 고급 기능
- 웹사이트 스크린샷 캡처
- PDF/이미지 OCR
- 동적 콘텐츠 크롤링 (Playwright)

## 참고 자료

- [httpx 공식 문서](https://www.python-httpx.org/)
- [BeautifulSoup 튜토리얼](https://www.crummy.com/software/BeautifulSoup/)
- [pandas I/O 도구](https://pandas.pydata.org/docs/user_guide/io.html)
- [robots.txt 표준](https://www.robotstxt.org/)
- [한국 개인정보보호법](https://www.law.go.kr/)
