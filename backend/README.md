# Backend — FastAPI API Gateway

## 개요

AgentForge 멀티 에이전트 플랫폼의 FastAPI 백엔드입니다. API Gateway, Discussion Engine, Pipeline Orchestrator, 공통 인프라로 구성됩니다.

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│                         HTTP/WebSocket                            │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                ┌─────────▼──────────┐
                │   gateway/         │  HTTP API, Auth, RBAC,
                │   - main.py        │  Rate Limiting, Cost Tracking
                │   - auth.py        │
                │   - rbac.py        │
                │   - rate_limiter   │
                │   - cost_tracker   │
                │   - session_mgr    │
                │   - routes/        │
                └─────┬──────┬───────┘
                      │      │
        ┌─────────────┘      └──────────────┐
        │                                    │
┌───────▼──────────┐              ┌─────────▼────────────┐
│  discussion/     │              │  pipeline/           │
│  - engine        │              │  - orchestrator      │
│  - intent        │              │  - graph_builder     │
│  - design        │              │  - llm_router        │
│  - critique      │              │  - state             │
│  - state_machine │              │  - agents/           │
│  - memory        │              │    - base            │
└──────────────────┘              │    - analyzer        │
                                  │    - collector       │
                                  │    - validator       │
                                  │    - synthesizer     │
                                  │    - reporter        │
                                  │    - custom          │
                                  │  - user_router_factory │
                                  │  - key_validator       │
                                  └──────────────────────┘
        │                                    │
        └─────────────┬──────────────────────┘
                      │
              ┌───────▼─────────┐
              │   shared/       │  DB, Config, Models,
              │   - database    │  Schemas, Security,
              │   - models      │  Metrics, Middleware
              │   - schemas     │
              │   - config      │
              │   - security    │
              │   - metrics     │
              │   - middleware  │
              │   - encryption  │
              └─────────────────┘
```

## 모듈 설명

### gateway/

API Gateway 레이어. HTTP/WebSocket 요청 처리, 인증/인가, 속도 제한, 비용 추적.

- **main.py**: FastAPI 앱 진입점, 라우터 등록, lifespan 관리
- **auth.py**: JWT 토큰 발급/검증, bcrypt 비밀번호 해싱, API 키 인증
- **rbac.py**: 역할 기반 접근 제어 (FREE/PRO/ADMIN 권한 매트릭스)
- **rate_limiter.py**: Redis 기반 속도 제한 (토큰 버킷 알고리즘)
- **cost_tracker.py**: 일일 LLM 비용 추적, Circuit Breaker (일일 한도 초과 시 차단)
- **session_manager.py**: Discussion Engine 세션 캐시 (Redis)
- **routes/auth.py**: 회원가입, 로그인, 토큰 갱신, 프로필 조회/수정
- **routes/chat.py**: WebSocket 채팅 (실시간 메시지 송수신)
- **routes/conversations.py**: 대화 이력 CRUD
- **routes/api_keys.py**: API 키 생성/조회/삭제
- **routes/pipeline.py**: 파이프라인 실행 (직접 실행, Discussion Engine 경유)
- **routes/templates.py**: 파이프라인 템플릿 관리 (CRUD, Fork, 공유)
- **routes/metrics.py**: Prometheus 메트릭 엔드포인트
- **routes/stats.py**: 사용량 통계 API (사용 이력, 파이프라인 이력)
- **routes/llm_keys.py**: BYOK LLM API 키 관리 (등록/조회/삭제/재검증, AES-256-GCM 암호화)

### discussion/

토론 기반 파이프라인 설계 엔진. 사용자와 대화하며 요구사항을 분석하고 최적 파이프라인을 제안.

- **engine.py**: 토론 오케스트레이터. 상태 머신 라우팅, 세션 관리
- **intent_analyzer.py**: 사용자 의도 분석 (LLM + 패턴 매칭 fallback)
- **design_generator.py**: 3개 대안 파이프라인 설계 생성 (속도 우선/품질 우선/균형)
- **critique_agent.py**: 설계 평가 및 1-10점 점수 산출
- **state_machine.py**: 유한 상태 머신 (UNDERSTAND → DESIGN → PRESENT → DEBATE → REFINE → CONFIRM → PLAN)
- **memory.py**: 토론 컨텍스트 (합의된 요구사항, 미결 질문, 사용자 선호도)

### pipeline/

LangGraph 기반 파이프라인 실행 엔진. Multi-LLM 라우팅, 에이전트 노드 구성.

- **orchestrator.py**: LangGraph 실행, 상태 스트리밍, 결과 집계
- **graph_builder.py**: DesignProposal을 LangGraph로 변환
- **llm_router.py**: Multi-LLM 라우팅 (OpenAI/Anthropic/Gemini, BYOK user_keys 주입 지원)
- **state.py**: TypedDict + Annotated + operator.add를 사용한 reducer 패턴
- **agents/base.py**: BaseAgentNode 추상 클래스 (재시도 로직, 프롬프트 인젝션 검사)
- **agents/analyzer.py**: 분석 에이전트 (사용자 요청 분해)
- **agents/collector.py**: 데이터 수집 에이전트 (Data Collector 마이크로서비스 호출)
- **agents/validator.py**: 검증 에이전트 (데이터 품질 검증)
- **agents/synthesizer.py**: 종합 에이전트 (결과 통합)
- **agents/reporter.py**: 보고 에이전트 (최종 리포트 생성)
- **agents/custom.py**: 사용자 정의 에이전트 (프롬프트 기반 임의 에이전트)
- **user_router_factory.py**: 사용자별 LLM Router 팩토리 (TTL 5분 캐시, 최대 200개)
- **key_validator.py**: Provider별 API 키 검증 (OpenAI: models.list, Anthropic: messages.create, Google: models.list)

### shared/

공통 인프라. DB, 설정, 모델, 스키마, 보안, 메트릭.

- **config.py**: 환경변수 설정 (Pydantic BaseSettings)
- **database.py**: SQLAlchemy async 세션 관리
- **models.py**: 8개 ORM 모델 (User, Conversation, Message, APIKey, PipelineExecution, PipelineTemplate, UserDailyCost, UserLLMKey)
- **schemas.py**: Pydantic 스키마 (Request/Response 검증)
- **security.py**: 2-Layer 프롬프트 인젝션 방어 (InputSanitizer + PromptIsolator)
- **metrics.py**: Prometheus 메트릭 정의 (요청 수, 레이턴시, 에러율, LLM 비용)
- **middleware.py**: HTTP 계측 미들웨어 (자동 메트릭 수집)
- **encryption.py**: AES-256-GCM 암호화/복호화 (BYOK API 키 보호, per-key random nonce)

## API 엔드포인트

### Auth

| Method | Path | 설명 |
|--------|------|------|
| POST | /auth/register | 회원가입 |
| POST | /auth/login | 로그인 (JWT 토큰 발급) |
| POST | /auth/refresh | 액세스 토큰 갱신 |
| GET | /auth/me | 현재 사용자 프로필 조회 |
| PUT | /auth/me | 프로필 수정 |
| GET | /auth/me/usage | 오늘 LLM 사용량 조회 |

### Chat

| Method | Path | 설명 |
|--------|------|------|
| WS | /ws/chat/{conversation_id} | WebSocket 채팅 |

### Conversations

| Method | Path | 설명 |
|--------|------|------|
| POST | /conversations | 새 대화 생성 |
| GET | /conversations | 내 대화 목록 조회 |
| GET | /conversations/{conversation_id} | 대화 상세 조회 |

### Pipelines

| Method | Path | 설명 |
|--------|------|------|
| POST | /pipelines/execute | Discussion Engine 경유 파이프라인 실행 |
| POST | /pipelines/execute-direct | 직접 파이프라인 실행 (템플릿 필수) |
| GET | /pipelines/{execution_id}/status | 실행 상태 조회 |
| GET | /pipelines/{execution_id}/result | 실행 결과 조회 |

### API Keys

| Method | Path | 설명 |
|--------|------|------|
| POST | /api-keys | API 키 생성 |
| GET | /api-keys | 내 API 키 목록 조회 |
| DELETE | /api-keys/{key_id} | API 키 삭제 |

### LLM Keys (BYOK)

| Method | Path | 설명 |
|--------|------|------|
| POST | /llm-keys | BYOK LLM 키 등록 (암호화 + 검증 + upsert) |
| GET | /llm-keys | 등록된 LLM 키 목록 (마스킹) |
| DELETE | /llm-keys/{key_id} | LLM 키 삭제 |
| POST | /llm-keys/{key_id}/validate | LLM 키 재검증 |

### Templates

| Method | Path | 설명 |
|--------|------|------|
| POST | /templates | 템플릿 생성 |
| GET | /templates | 내 템플릿 목록 조회 |
| GET | /templates/shared | 공유 템플릿 조회 |
| GET | /templates/{template_id} | 템플릿 상세 조회 |
| PUT | /templates/{template_id} | 템플릿 수정 |
| DELETE | /templates/{template_id} | 템플릿 삭제 |
| POST | /templates/{template_id}/fork | 템플릿 포크 |

### Metrics

| Method | Path | 설명 |
|--------|------|------|
| GET | /metrics | Prometheus 메트릭 |

### Stats

| Method | Path | 설명 |
|--------|------|------|
| GET | /stats/usage-history?days=30 | 일별 사용량/비용 이력 |
| GET | /stats/pipeline-history?limit=20 | 파이프라인 실행 이력 |

### Health

| Method | Path | 설명 |
|--------|------|------|
| GET | /health | 헬스체크 |

## 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| DATABASE_URL | PostgreSQL 연결 URL | postgresql+asyncpg://user:password@db:5432/agentforge |
| REDIS_URL | Redis 연결 URL | redis://redis:6379/0 |
| SECRET_KEY | JWT 서명 키 (프로덕션 필수) | - |
| CORS_ORIGINS | CORS 허용 Origin | http://localhost:3000 |
| DEBUG | 디버그 모드 | False |
| JWT_ALGORITHM | JWT 알고리즘 | HS256 |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 액세스 토큰 만료 시간 | 30 |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | 리프레시 토큰 만료 시간 | 7 |
| OPENAI_API_KEY | OpenAI API 키 | - |
| ANTHROPIC_API_KEY | Anthropic API 키 | - |
| DEFAULT_LLM_PROVIDER | 기본 LLM 제공자 | anthropic |
| DEFAULT_LLM_MODEL | 기본 LLM 모델 | claude-3-5-sonnet-20241022 |
| DATA_COLLECTOR_URL | Data Collector 서비스 URL | http://data-collector:8001 |
| ENCRYPTION_KEY | BYOK API 키 암호화용 AES-256 키 | - |
| GOOGLE_API_KEY | Google Gemini API 키 | - |

## 보안

### 인증/인가

- **JWT + API Key 이중 인증**: 웹 UI는 JWT, 외부 API는 API 키 사용
- **RBAC (Role-Based Access Control)**: FREE/PRO/ADMIN 역할별 권한 매트릭스
  - FREE: 3 pipelines/day, 일일 비용 한도 $1
  - PRO: 100 pipelines/day, 일일 비용 한도 $50
  - ADMIN: 무제한

### 프롬프트 인젝션 방어

2-Layer 방어 체계 (shared/security.py):

1. **InputSanitizer**: 입력 검증 및 위험 패턴 제거
2. **PromptIsolator**: XML 태그로 사용자 입력 격리 (`<user_input>...</user_input>`)

### IDOR (Insecure Direct Object Reference) 방지

- 모든 리소스 접근 시 소유권 검증
- 존재하지 않는 리소스와 권한 없는 리소스를 동일하게 404 처리 (Oracle 공격 방지)

### TOCTOU (Time-Of-Check Time-Of-Use) Safety

- 파이프라인 실행 시 Redis lock으로 동시성 제어
- 비용 추적 시 Redis pipeline으로 원자성 보장

### BYOK (Bring Your Own Key)

- **암호화**: AES-256-GCM + per-key random nonce로 API 키 암호화 저장
- **최소 노출**: 복호화는 파이프라인 실행 시에만, API 응답/로그에 평문 키 없음
- **키 프리픽스**: 첫 12자만 표시용으로 저장 (key_prefix)
- **TTL 캐시**: 5분 TTL, 최대 200개 — 메모리 내 키 수명 제한
- **캐시 무효화**: 키 CRUD 시 즉시 캐시 무효화

### 비용 Circuit Breaker

- 사용자별 일일 LLM 비용 추적 (UserDailyCost 모델)
- 일일 한도 초과 시 429 Too Many Requests 반환

## 실행 방법

## 데이터베이스 마이그레이션

Alembic으로 스키마를 관리합니다. Docker 환경에서는 `entrypoint.sh`가 자동으로 `alembic upgrade head`를 실행합니다.

```bash
# 마이그레이션 실행
cd backend
python -m alembic upgrade head

# 마이그레이션 상태 확인
python -m alembic current

# 새 마이그레이션 생성
python -m alembic revision -m "description"
```

## 실행 방법

### 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/agentforge"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your-secret-key-here"
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# 서버 실행
cd backend
uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose

```bash
# 루트 디렉토리에서 실행
docker compose up backend
```

## 테스트

```bash
# 전체 테스트 실행
cd backend
python -m pytest ../tests/ -v --tb=short

# 특정 Phase 테스트만 실행
python -m pytest ../tests/unit/backend/gateway/test_auth.py -v  # Phase 2A
python -m pytest ../tests/unit/backend/discussion/ -v           # Phase 3
python -m pytest ../tests/unit/backend/pipeline/ -v             # Phase 5

# 커버리지 리포트
python -m pytest ../tests/ --cov=. --cov-report=html
```

## 라이선스

MIT
