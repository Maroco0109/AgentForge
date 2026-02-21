# AgentForge

사용자 프롬프트 기반 멀티 에이전트 플랫폼. 자연어로 요구사항을 입력하면 AI가 "동업자"처럼 설계를 토론하고, 에이전트 기반 파이프라인을 자동 설계/실행합니다.

## 핵심 차별점

- **심층 토론 기반 설계**: AI가 동업자 역할로 3-5라운드 대화를 통해 요구사항을 분석하고 설계안을 제시
- **Multi-LLM 라우팅**: OpenAI, Anthropic 모델을 작업 복잡도에 따라 자동 선택하여 비용 60-70% 절감
- **데이터 수집 적법성 자동 검증**: robots.txt, PII 탐지, 사이트별 Rate Limiting 내장
- **한국어 네이티브 지원**: 한국어 의도 분석 및 패턴 매칭

## 아키텍처

```
[사용자 브라우저]
       │ WebSocket + REST
       ▼
[Frontend - Next.js 14]
       │
       ▼
[API Gateway - FastAPI]
  ├── JWT 인증 (Phase 2A ✅)
  ├── RBAC + Rate Limiting (Phase 2B)
  │
  ├──→ [Discussion Engine]
  │      ├── Intent Analyzer (Phase 3 ✅)
  │      ├── Design Generator (Phase 4)
  │      └── Critique Agent (Phase 4)
  │
  ├──→ [Pipeline Orchestrator - LangGraph] (Phase 5)
  │
  └──→ [Data Collector 마이크로서비스] (Phase 6 ✅)
         ├── Compliance Gateway (robots.txt, PII, Rate Limiter)
         ├── Web Crawler / API Fetcher / File Reader
         └── Processing Pipeline (Cleaner, Anonymizer, Chunker)
```

## 기술 스택

| 계층 | 기술 |
|------|------|
| Frontend | Next.js 14, React 18, TypeScript |
| Backend | FastAPI, Python 3.11+ |
| 인증 | JWT (PyJWT), bcrypt |
| 에이전트 | LangGraph (예정) |
| LLM | OpenAI + Anthropic (Multi-LLM Router) |
| DB | PostgreSQL 16+, SQLAlchemy + Alembic |
| 캐시 | Redis 7+ |
| 컨테이너 | Docker Compose |

## 프로젝트 구조

```
AgentForge/
├── frontend/                    # Next.js 14 App Router
│   ├── app/
│   │   ├── page.tsx             # 메인 챗봇 페이지
│   │   ├── layout.tsx           # 루트 레이아웃
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx   # 채팅 UI
│   │   │   └── MessageBubble.tsx
│   │   └── api/                 # API 라우트
│   └── lib/
│       ├── auth.ts              # 인증 유틸
│       └── websocket.ts         # WebSocket 클라이언트
│
├── backend/                     # FastAPI 백엔드
│   ├── gateway/
│   │   ├── main.py              # FastAPI 앱 진입점
│   │   ├── auth.py              # JWT 인증 미들웨어
│   │   └── routes/
│   │       └── auth.py          # 인증 API (/register, /login, /me, /refresh)
│   ├── discussion/
│   │   ├── engine.py            # Discussion Engine
│   │   └── intent_analyzer.py   # 의도 분석 (LLM + 패턴 매칭)
│   ├── pipeline/
│   │   ├── llm_router.py        # Multi-LLM 라우터
│   │   └── agents/              # 에이전트 타입 정의
│   ├── shared/
│   │   ├── config.py            # 환경변수 설정
│   │   ├── database.py          # DB 연결
│   │   ├── models.py            # SQLAlchemy 모델
│   │   ├── schemas.py           # Pydantic 스키마
│   │   └── security.py          # 프롬프트 인젝션 방어
│   └── alembic/                 # DB 마이그레이션
│
├── data-collector/              # 독립 마이크로서비스
│   ├── main.py                  # FastAPI 앱
│   ├── schemas.py               # 요청/응답 스키마 (SSRF 방어 포함)
│   ├── config.py                # 설정
│   ├── compliance/
│   │   ├── robots_checker.py    # robots.txt 검증
│   │   ├── pii_detector.py      # 한국어 PII 탐지
│   │   └── rate_limiter.py      # 사이트별 Rate Limiting
│   ├── collectors/
│   │   ├── web_crawler.py       # Playwright + BeautifulSoup
│   │   ├── api_fetcher.py       # httpx async
│   │   └── file_reader.py       # CSV/Excel/JSON
│   ├── processing/
│   │   ├── cleaner.py           # HTML 태그 제거
│   │   ├── anonymizer.py        # PII 비식별화
│   │   └── chunker.py           # LLM 처리용 청크 분할
│   └── tests/                   # Data Collector 테스트
│
├── tests/                       # 통합 테스트
│   ├── unit/                    # 유닛 테스트
│   ├── integration/             # 통합 테스트
│   └── e2e/                     # E2E 테스트
│
├── docker/                      # Docker 설정
│   ├── docker-compose.yml
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   └── Dockerfile.collector
│
├── docs/                        # Phase별 문서
│   ├── phase-01-foundation.md
│   ├── phase-02a-auth.md
│   ├── phase-03-intent-analyzer.md
│   └── phase-06-data-collector.md
│
└── .github/workflows/           # CI/CD
    ├── test.yml                 # pytest + frontend build
    ├── lint.yml                 # ruff + ESLint
    ├── claude-code-review.yml   # AI 코드 리뷰
    └── auto-fix.yml             # 자동 수정
```

## 구현 진행 상황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 프로젝트 기반 + 챗봇 UI | ✅ 완료 |
| Phase 2A | JWT 인증 (회원가입/로그인/토큰 갱신) | ✅ 완료 |
| Phase 2B | RBAC + Rate Limiting | 예정 |
| Phase 2C | API 키 관리 | 예정 |
| Phase 3 | Intent Analyzer + Multi-LLM 라우터 | ✅ 완료 |
| Phase 4 | Design Generator + Critique Agent | 예정 |
| Phase 5 | Pipeline Orchestrator (LangGraph) | 예정 |
| Phase 6 | Data Collector 마이크로서비스 | ✅ 완료 |
| Phase 7 | 서비스 연동 + E2E 통합 | 예정 |
| Phase 8 | 개발자 고급 모드 (React Flow) | 예정 |

## 시작하기

### 사전 요구사항

- Docker 24.0+ / Docker Compose 2.20+
- Node.js 20+ (프론트엔드 개발)
- Python 3.11+ (백엔드 개발)

### Docker로 실행

```bash
git clone https://github.com/Maroco0109/AgentForge.git
cd AgentForge

# 환경변수 설정
cp backend/.env.example backend/.env
# .env 파일에 SECRET_KEY, OPENAI_API_KEY 등 설정

# 서비스 시작
docker-compose up -d
```

| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:8000 |
| Data Collector | http://localhost:8001 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 로컬 개발

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn gateway.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Data Collector
cd data-collector
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 테스트

```bash
# Backend 테스트
cd backend && python -m pytest ../tests/ -v

# Data Collector 테스트
cd data-collector && python -m pytest tests/ -v

# Frontend 빌드 검증
cd frontend && npm run build
```

## 브랜치 전략

```
feat/phase-N-xxx ──PR──→ develop ──PR──→ main
```

- `main`: E2E 테스트 완료된 안정 코드
- `develop`: Phase별 머지 브랜치
- `feat/*`: 기능 개발 브랜치

### 커밋 컨벤션

```
<type>(<scope>): <subject> (#이슈번호)

feat: 새 기능  |  fix: 버그 수정  |  refactor: 리팩토링
test: 테스트   |  docs: 문서      |  chore: 설정/유지보수
```

## CI/CD

모든 PR에 5개 자동 체크가 실행됩니다:

| Check | 내용 |
|-------|------|
| backend-test | pytest 백엔드 테스트 |
| backend-lint | ruff format + check |
| frontend-build | Next.js 프로덕션 빌드 |
| frontend-lint | ESLint 검사 |
| claude-review | AI 코드 리뷰 |

## 라이선스

MIT License - Copyright (c) 2024 AgentForge
