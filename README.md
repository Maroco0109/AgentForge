# AgentForge

![Backend Tests](https://github.com/Maroco0109/AgentForge/actions/workflows/test.yml/badge.svg)
![Frontend Build](https://github.com/Maroco0109/AgentForge/actions/workflows/test.yml/badge.svg)
![E2E Tests](https://github.com/Maroco0109/AgentForge/actions/workflows/e2e.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

사용자 프롬프트 기반 멀티 에이전트 플랫폼. 자연어로 요구사항을 설명하면 AI가 토론하고 설계한 후, 에이전트 기반 파이프라인을 자동 실행합니다.

## 핵심 차별점

1. **심층 토론 기반 설계**: Intent Analyzer → Design Generator → Critique Agent의 3단계 토론 프로세스로 요구사항을 정제하고 최적의 파이프라인을 설계합니다.
2. **Multi-LLM 라우팅 (비용 60-70% 절감)**: 작업 복잡도에 따라 GPT-4o, GPT-4o-mini, Claude Sonnet을 자동 선택하여 성능과 비용을 최적화합니다.
3. **데이터 수집 적법성 자동 검증**: robots.txt 준수, IP 기반 SSRF 방어, DNS rebinding 방어를 내장한 독립 마이크로서비스로 크롤링 위험을 최소화합니다.
4. **한국어 네이티브 지원**: Intent Analyzer부터 UI까지 전 계층이 한국어를 우선 지원합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js 14)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐    │
│  │   Chat UI   │  │ Auth UI      │  │ React Flow Pipeline Editor │    │
│  └─────────────┘  └──────────────┘  └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼ (HTTP/WebSocket)
┌─────────────────────────────────────────────────────────────────────────┐
│                        API Gateway (FastAPI)                            │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────────┐     │
│  │ JWT Auth     │  │ RBAC          │  │ Rate Limiting           │     │
│  │ API Key Mgmt │  │ Cost Breaker  │  │ Prometheus Metrics      │     │
│  └──────────────┘  └───────────────┘  └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Discussion Engine                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Intent Analyzer  │→ │ Design Generator │→ │ Critique Agent   │     │
│  │ (Multi-LLM)      │  │ (Multi-LLM)      │  │ (Multi-LLM)      │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Pipeline Orchestrator (LangGraph)                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  StateGraph: [router] → [intent/design/critique] → [merge]      │  │
│  │  Features: 병렬 실행, 상태 체크포인트, 에러 복구                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                Data Collector (독립 마이크로서비스)                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  robots.txt 준수, SSRF 방어, IP/DNS 차단, 적법성 검증            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌────────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ PostgreSQL 16+ │  │  Redis 7+   │  │  Prometheus  │  │   Grafana    │
│ (SQLAlchemy)   │  │  (Cache)    │  │  (Metrics)   │  │ (Dashboard)  │
└────────────────┘  └─────────────┘  └──────────────┘  └──────────────┘
```

## 기술 스택

| 계층 | 기술 |
|------|------|
| **Frontend** | Next.js 14, React 18, TypeScript, React Flow |
| **Backend** | FastAPI, Python 3.11+ |
| **인증/인가** | JWT, bcrypt, RBAC, API Key 관리, Cost Circuit Breaker |
| **에이전트** | LangGraph |
| **LLM** | OpenAI (GPT-4o, GPT-4o-mini) + Anthropic (Claude Sonnet) Multi-LLM Router |
| **데이터베이스** | PostgreSQL 16+, SQLAlchemy (async), Alembic (마이그레이션) |
| **캐시** | Redis 7+ |
| **모니터링** | Prometheus, Grafana |
| **컨테이너** | Docker Compose |
| **테스트** | pytest, pytest-asyncio, Vitest, React Testing Library, Playwright |
| **CI/CD** | GitHub Actions (7 checks) |

## 프로젝트 구조

```
.
├── backend/                      # FastAPI 백엔드
│   ├── gateway/                  # API Gateway (JWT, RBAC, Rate Limiting, API Key)
│   │   │   ├── auth.py               # JWT 인증
│   │   ├── rbac.py               # 역할 기반 접근 제어
│   │   ├── limiter.py            # Rate Limiting
│   │   ├── api_key_manager.py    # API 키 관리
│   │   ├── cost_breaker.py       # 비용 Circuit Breaker
│   │   └── routes/stats.py       # 사용량 통계 API
│   ├── discussion/               # Discussion Engine
│   │   ├── intent_analyzer.py    # 의도 분석
│   │   ├── design_generator.py   # 설계 생성
│   │   └── critique_agent.py     # 비평 에이전트
│   ├── pipeline/                 # Pipeline Orchestrator (LangGraph)
│   │   ├── graph.py              # StateGraph 정의
│   │   └── session.py            # 세션 관리
│   └── shared/                   # 공유 모듈
│       ├── models.py             # SQLAlchemy 모델 (7개)
│       ├── database.py           # DB 세션 팩토리 (Alembic 마이그레이션 지원)
│       ├── schemas.py            # Pydantic 스키마
│       ├── security.py           # 프롬프트 인젝션 방어
│       ├── metrics.py            # Prometheus 메트릭
│       └── middleware.py         # 미들웨어 (메트릭 수집)
├── data-collector/               # 독립 마이크로서비스
│   ├── main.py                   # FastAPI 엔드포인트
│   ├── collector.py              # 데이터 수집 로직
│   ├── schemas.py                # SSRF 방어 스키마
│   └── tests/                    # 단위 테스트
├── frontend/                     # Next.js 14 App Router
│   ├── app/                      # App Router
│   │   ├── (auth)/               # 인증 페이지 (login, register)
│   │   ├── (main)/               # 메인 페이지
│   │   │   ├── conversations/    # 대화 목록/상세
│   │   │   ├── dashboard/        # 사용자 대시보드 (사용량 차트, 파이프라인 이력)
│   │   │   └── templates/        # 템플릿 목록/상세
│   │   ├── components/           # React 컴포넌트
│   │   │   ├── ChatWindow.tsx    # WebSocket 채팅
│   │   │   ├── SplitView.tsx     # 분할 패널
│   │   │   └── pipeline-editor/  # React Flow 파이프라인 에디터
│   │   └── page.tsx              # 홈 (SplitView)
│   ├── lib/                      # 유틸리티 (API, WebSocket, Auth Context)
│   └── vitest.config.ts          # Vitest 테스트 설정
├── tests/                        # 백엔드 통합 테스트
│   ├── unit/                     # 단위 테스트
│   │   ├── test_auth.py          # JWT 인증
│   │   ├── test_rbac.py          # RBAC
│   │   ├── test_limiter.py       # Rate Limiting
│   │   ├── test_api_key.py       # API 키 관리
│   │   ├── test_cost_breaker.py  # 비용 Circuit Breaker
│   │   ├── test_discussion.py    # Discussion Engine
│   │   ├── test_pipeline.py      # Pipeline Orchestrator
│   │   └── test_session.py       # 세션 관리
│   ├── integration/              # 통합 테스트
│   │   ├── test_e2e_flow.py      # Phase 7 E2E 통합
│   │   └── test_llm_real.py      # LLM 실제 API 테스트
│   └── conftest.py               # pytest 설정
├── e2e/                          # Playwright E2E 테스트
│   ├── tests/                    # 테스트 스크립트
│   │   ├── helpers.ts            # 공통 헬퍼 (인증, 템플릿 생성 등)
│   │   ├── auth.spec.ts          # 로그인/회원가입
│   │   ├── chat.spec.ts          # 챗봇 대화
│   │   ├── smoke.spec.ts         # 스모크 테스트
│   │   ├── pipeline-editor.spec.ts # 파이프라인 에디터
│   │   └── templates.spec.ts     # 템플릿 CRUD
│   └── playwright.config.ts      # Playwright 설정
├── docker/                       # Docker Compose 설정
│   ├── docker-compose.yml        # 전체 서비스
│   ├── prometheus/               # Prometheus 설정
│   │   └── prometheus.yml        # 스크랩 설정
│   └── grafana/                  # Grafana 설정
│       ├── provisioning/         # 데이터소스/대시보드 자동 설정
│       └── dashboards/           # 대시보드 JSON
├── docs/                         # Phase별 문서
│   ├── phase-01-foundation.md    # Phase 1 문서
│   ├── phase-02a-jwt-auth.md     # Phase 2A 문서
│   ├── phase-02b-rbac-rl.md      # Phase 2B 문서
│   ├── phase-02c-api-key.md      # Phase 2C 문서
│   ├── phase-03-discussion.md    # Phase 3 문서
│   ├── phase-04-agents.md        # Phase 4 문서
│   ├── phase-05-pipeline.md      # Phase 5 문서
│   ├── phase-06-collector.md     # Phase 6 문서
│   ├── phase-07-integration.md   # Phase 7 문서
│   └── phase-08-react-flow.md    # Phase 8 문서
├── .github/workflows/            # CI/CD
│   ├── test.yml                  # backend-test, backend-lint, frontend-build, frontend-lint, frontend-test
│   ├── e2e.yml                   # E2E 테스트 (Playwright + Docker)
│   └── claude-code-review.yml    # AI 코드 리뷰
├── .env.example                  # 환경변수 예시
├── pyproject.toml                # Python 의존성
├── README.md                     # 이 파일
└── ROADMAP.md                    # 로드맵
```

## 구현 진행 상황

| Phase | 상태 | 설명 |
|-------|------|------|
| **Phase 1** | ✅ 완료 | 프로젝트 기반 + 챗봇 UI (FastAPI + Next.js 14 + WebSocket) |
| **Phase 2A** | ✅ 완료 | JWT 인증 (bcrypt, access/refresh token) |
| **Phase 2B** | ✅ 완료 | RBAC + Rate Limiting (역할 기반 접근 제어, Redis 기반 속도 제한) |
| **Phase 2C** | ✅ 완료 | API 키 관리 + 비용 Circuit Breaker (일일 비용 한도, TOCTOU 방지) |
| **Phase 3** | ✅ 완료 | Intent Analyzer + Multi-LLM 라우터 (복잡도 기반 모델 선택) |
| **Phase 4** | ✅ 완료 | Design Generator + Critique Agent (설계 생성 및 비평) |
| **Phase 5** | ✅ 완료 | Pipeline Orchestrator (LangGraph StateGraph, 병렬 실행, 체크포인트) |
| **Phase 6** | ✅ 완료 | Data Collector 마이크로서비스 (robots.txt, SSRF 방어, 적법성 검증) |
| **Phase 7** | ✅ 완료 | 서비스 연동 + E2E 통합 (SessionManager, CollectorNode, 프론트엔드 메시지 라우팅) |
| **Phase 8** | ✅ 완료 | React Flow 파이프라인 에디터 (노드 기반 시각적 파이프라인 편집) |
| **Monitoring** | ✅ 완료 | Prometheus + Grafana (9개 패널: HTTP, LLM, Pipeline, WebSocket 메트릭) |
| **LLM 통합 테스트** | ✅ 완료 | OpenAI/Anthropic 실제 API 호출 검증 |
| **E2E CI** | ✅ 완료 | Playwright 기반 E2E 테스트 자동화 |

## 시작하기

### 사전 요구사항

- Docker 24+
- Node.js 20+
- Python 3.11+

### Docker로 실행 (권장)

```bash
# 리포지토리 클론
git clone https://github.com/Maroco0109/AgentForge.git
cd AgentForge

# 환경변수 설정
cp .env.example .env
# .env 파일에서 SECRET_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY 설정

# Docker Compose로 전체 서비스 실행
cd docker
docker compose up -d
```

### 서비스 URL

| 서비스 | URL | 계정 |
|--------|-----|------|
| **Frontend** | http://localhost:3000 | - |
| **API Gateway** | http://localhost:8000 | - |
| **Data Collector** | http://localhost:8001 | - |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **PostgreSQL** | localhost:5432 | user: agentforge, db: agentforge |
| **Redis** | localhost:6379 | - |

### 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `SECRET_KEY` | JWT 서명 키 (필수, 프로덕션) | - |
| `OPENAI_API_KEY` | OpenAI API 키 (필수) | - |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (필수) | - |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | postgresql+asyncpg://... |
| `REDIS_URL` | Redis 연결 문자열 | redis://localhost:6379 |
| `NEXT_PUBLIC_API_URL` | 프론트엔드에서 사용할 API URL | http://localhost:8000 |
| `NEXT_PUBLIC_WS_URL` | 프론트엔드에서 사용할 WebSocket URL | ws://localhost:8000 |
| `DATA_COLLECTOR_URL` | Data Collector 서비스 URL | http://localhost:8001 |
| `DAILY_COST_LIMIT` | 일일 비용 한도 (USD) | 10.0 |
| `DEBUG` | 디버그 모드 (개발 시) | false |

### 로컬 개발 (Docker 없이)

```bash
# PostgreSQL, Redis 실행 (Docker 또는 로컬 설치)
docker compose -f docker/docker-compose.yml up -d postgres redis

# 백엔드 (Gateway + Discussion)
cd backend
pip install -e .
alembic upgrade head
uvicorn backend.gateway.main:app --reload --port 8000

# Data Collector
cd data-collector
pip install -e .
uvicorn data_collector.main:app --reload --port 8001

# 프론트엔드
cd frontend
npm install
npm run dev
```

## 테스트

### 백엔드 단위/통합 테스트

```bash
cd backend
python -m pytest ../tests/ -v --tb=short
```

### Data Collector 테스트

```bash
cd data-collector
python -m pytest tests/ -v --tb=short
```

### LLM 통합 테스트 (OpenAI API 키 필요)

```bash
OPENAI_API_KEY=sk-xxx pytest tests/integration/test_llm_real.py -v -m llm_integration
```

### E2E 테스트 (Docker 필요)

```bash
# 전체 서비스 실행
cd docker
docker compose up -d

# E2E 테스트 실행
cd ../e2e
npx playwright test
```

### 프론트엔드 단위 테스트

```bash
cd frontend
npm test
```

### 프론트엔드 빌드 검증

```bash
cd frontend
npm run build
```

### 린트

```bash
# 백엔드
ruff format backend/
ruff check backend/

# 프론트엔드
cd frontend
npm run lint
```

## CI/CD

모든 PR은 7개 체크를 통과해야 머지 가능합니다:

| 체크 | 워크플로우 | 설명 |
|------|-----------|------|
| **backend-test** | test.yml | pytest (backend + data-collector) |
| **backend-lint** | test.yml | ruff format + check |
| **frontend-build** | test.yml | Next.js 프로덕션 빌드 |
| **frontend-lint** | test.yml | ESLint |
| **frontend-test** | test.yml | Vitest 단위 테스트 (43개) |
| **e2e** | e2e.yml | Playwright E2E 테스트 (Docker) |
| **claude-review** | claude-code-review.yml | AI 코드 리뷰 (Claude Sonnet 4.6) |

## 모니터링

### Prometheus

- URL: http://localhost:9090
- 메트릭: HTTP 요청/응답, LLM 토큰/비용, 파이프라인 상태, WebSocket 연결

### Grafana

- URL: http://localhost:3001 (admin/admin)
- 9개 패널 대시보드:
  1. **HTTP Request Rate**: 초당 HTTP 요청 수
  2. **HTTP Latency (p50/p95/p99)**: HTTP 응답 지연 시간 백분위수
  3. **Error Rate**: 5xx 에러 비율
  4. **LLM Token Usage**: LLM별 토큰 사용량
  5. **LLM Cost Tracking**: LLM별 누적 비용 (USD)
  6. **LLM Request Latency**: LLM API 호출 지연 시간
  7. **Pipeline Execution Status**: 파이프라인 실행 상태 (성공/실패)
  8. **Pipeline Duration**: 파이프라인 실행 시간
  9. **Active WebSocket Connections**: 활성 WebSocket 연결 수

## 로드맵

자세한 로드맵은 [ROADMAP.md](./ROADMAP.md)를 참조하세요.

## 기여 가이드

### 브랜치 전략

```
feat/phase-N-xxx → develop → main
```

- `main`: 안정 코드만 (프로덕션 준비)
- `develop`: Phase 머지 브랜치
- 브랜치 생성은 반드시 `develop`에서 분기

### 커밋 메시지

```
<type>(<scope>): <subject> (#이슈번호)
```

- `type`: feat, fix, refactor, test, docs, chore
- 예: `feat(auth): add JWT refresh token (#10)`

### Pull Request

1. Issue 생성
2. `develop`에서 브랜치 생성 (`feat/phase-N-xxx`)
3. 구현 + 테스트 작성
4. 커밋 (컨벤션 준수)
5. PR 생성 (템플릿 사용)
6. **CI 7개 체크 전부 통과 대기** (backend-test, backend-lint, frontend-build, frontend-lint, frontend-test, e2e, claude-review)
7. **claude-review 코멘트 확인 및 수정**
8. 사용자 리뷰 후 머지

## 라이선스

[MIT License](./LICENSE)
