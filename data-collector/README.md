# Data Collector — 독립 마이크로서비스

## 개요

Data Collector는 FastAPI 기반 독립 마이크로서비스로, 웹 크롤링, API 수집, 파일 처리를 수행하며 적법성 검증과 PII(개인식별정보) 탐지/비식별화 기능을 제공합니다.

주요 기능:
- 다양한 데이터 소스 수집 (웹, REST/GraphQL API, CSV/Excel/JSON 파일)
- robots.txt 준수 및 도메인별 Rate Limiting
- SSRF(Server-Side Request Forgery) 공격 방어
- 한국어 PII 6종 탐지 및 비식별화
- 문장 경계 기반 청킹 및 데이터 전처리

## 아키텍처

```
Collection Request
        |
        v
   Compliance
   (robots.txt, Rate Limit)
        |
        v
    Collectors
   (Web/API/File)
        |
        v
    Processing
   (Clean → PII Detect → Anonymize → Chunk)
        |
        v
   Data Response
```

## 모듈 설명

### 핵심 모듈

#### main.py
6개 엔드포인트를 제공하는 FastAPI 애플리케이션:
- `GET /api/v1/health`: 헬스 체크
- `GET /metrics`: Prometheus 메트릭
- `POST /api/v1/collections`: 수집 작업 생성
- `GET /collections/{id}/status`: 수집 작업 상태 조회
- `POST /collections/{id}/compliance`: 적법성 검증 수행
- `POST /collections/{id}/collect`: 데이터 수집 실행
- `GET /collections/{id}/data`: 수집된 데이터 조회

#### schemas.py
SSRF 방어가 내장된 Pydantic 스키마:
- IP 주소 직접 차단 (private, loopback, link-local, multicast)
- 호스트네임 블랙리스트 검증
- DNS Resolution 후 재검증

#### config.py
pydantic_settings 기반 환경변수 관리 (BaseSettings 사용)

### 적법성 검증 (Compliance)

#### compliance/robots_checker.py
- robots.txt 파싱 및 준수 여부 확인
- 30분 TTL 캐시 (메모리 기반)
- User-Agent별 허용/차단 규칙 적용

#### compliance/rate_limiter.py
- 도메인별 asyncio 기반 Rate Limiting
- 기본 2초 대기 시간 (환경변수로 설정 가능)
- 비동기 작업에 최적화

#### compliance/pii_detector.py
한국어 PII 6종 탐지:
1. 전화번호 (010-1234-5678)
2. 이메일 (user@example.com)
3. 주민등록번호 (123456-1234567)
4. 카드번호 (1234-5678-9012-3456)
5. 이름+직함 (홍길동 대리)
6. 주소 (서울시 강남구 테헤란로 123)

### 데이터 수집 (Collectors)

#### collectors/web_crawler.py
- httpx + BeautifulSoup 기반 웹 크롤링
- title, 본문 텍스트, 링크 목록 추출
- HTML 태그 제거 및 텍스트 정리

#### collectors/api_fetcher.py
- REST/GraphQL API 클라이언트
- GET/POST 메서드 지원
- JSON 응답 파싱

#### collectors/file_reader.py
- CSV/Excel/JSON/JSONL 파일 처리 (pandas 사용)
- 최대 1000행 제한
- 자동 인코딩 감지

### 데이터 전처리 (Processing)

#### processing/cleaner.py
3단계 정제:
1. HTML unescape (예: `&lt;` → `<`)
2. HTML 태그 제거
3. Unicode NFC 정규화 (한글 조합 문자 통일)

#### processing/anonymizer.py
PII → 한국어 대체 토큰 변환:
- 이메일 → `[이메일]`
- 전화번호 → `[전화번호]`
- 주민등록번호 → `[주민등록번호]`
- 카드번호 → `[카드번호]`
- 이름+직함 → `[이름]`
- 주소 → `[주소]`

#### processing/chunker.py
문장 경계 기반 청킹:
- 기본 청크 크기: 1000자
- 오버랩: 200자
- 한국어/영어 문장 경계 인식 (`.`, `!`, `?` 기준)

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/health` | 헬스 체크 |
| GET | `/metrics` | Prometheus 메트릭 |
| POST | `/api/v1/collections` | 수집 작업 생성 |
| GET | `/collections/{id}/status` | 수집 작업 상태 조회 |
| POST | `/collections/{id}/compliance` | 적법성 검증 수행 |
| POST | `/collections/{id}/collect` | 데이터 수집 실행 |
| GET | `/collections/{id}/data` | 수집된 데이터 조회 |

## SSRF 방어 3계층

### Layer 1: IP 주소 직접 검사
다음 IP 범위를 차단:
- Private: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- Loopback: 127.0.0.0/8, ::1
- Link-local: 169.254.0.0/16, fe80::/10
- Multicast: 224.0.0.0/4, ff00::/8

### Layer 2: 호스트네임 블랙리스트
다음 호스트네임 패턴을 차단:
- `localhost`, `127.0.0.1`, `::1`
- `metadata.google.internal`
- `.internal` 도메인
- `.local` 도메인

### Layer 3: DNS Resolution 검증
URL의 호스트네임을 DNS로 해석한 후, 해석된 IP가 private 범위인지 재검사하여 DNS rebinding 공격 방어.

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 연결 URL | `postgresql+asyncpg://user:pass@localhost/db` |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` |
| `DEFAULT_RATE_LIMIT_SECONDS` | 도메인별 Rate Limit 대기 시간 (초) | `2.0` |
| `MAX_COLLECTION_SIZE_MB` | 수집 가능한 최대 데이터 크기 (MB) | `100` |
| `PII_DETECTION_ENABLED` | PII 탐지 기능 활성화 여부 | `true` |

## 실행 방법

### 로컬 실행

```bash
cd data-collector
pip install -r requirements.txt

# 환경변수 설정 (선택사항)
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/agentforge"
export REDIS_URL="redis://localhost:6379/0"

# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker 실행

```bash
docker-compose up data-collector
```

### 테스트

```bash
cd data-collector
python -m pytest tests/ -v --tb=short
```

전체 테스트 (backend + data-collector):
```bash
cd backend
python -m pytest ../tests/ -v --tb=short
```

## 보안 고려사항

1. **SSRF 방어**: 3계층 검증으로 내부 네트워크 접근 차단
2. **PII 보호**: 자동 탐지 및 비식별화로 개인정보 유출 방지
3. **Rate Limiting**: DoS 공격 및 과도한 크롤링 방지
4. **robots.txt 준수**: 웹사이트의 크롤링 정책 존중
5. **크기 제한**: MAX_COLLECTION_SIZE_MB로 메모리 소진 방지

## 라이선스

MIT License
