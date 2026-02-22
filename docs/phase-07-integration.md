# Phase 7: 서비스 연동 + E2E 통합

## 개요

Phase 1~6에서 구축한 4개의 독립 서비스를 연결하여 전체 흐름을 완성했습니다.

- **Frontend** (Next.js) → WebSocket → **Gateway** (FastAPI)
- **Gateway** → **DiscussionEngine** (Intent → Design → Critique → Plan)
- **DiscussionEngine** → **PipelineOrchestrator** (LangGraph 실행)
- **PipelineOrchestrator** → **Data Collector** (HTTP API)

## 아키텍처

```
[사용자 브라우저]
       │ WebSocket + REST
       ▼
[Frontend - Next.js]
  - 챗봇 UI (메시지 타입별 렌더링)
  - 토론 상태 표시 (설계안, 비평, 질문)
  - 파이프라인 실행 진행률 표시
       │ WebSocket (?token=JWT)
       ▼
[API Gateway - FastAPI]
  - JWT 인증 (WebSocket query param)
  - SessionManager (conversation별 DiscussionEngine)
  - 메시지 DB 저장 (AsyncSessionLocal)
       │
  ┌────┴────────────┐
  ▼                 ▼
[DiscussionEngine]  [PipelineOrchestrator]
  - Intent분석       - LangGraph 그래프 실행
  - 설계안 생성       - on_status 콜백 → WS
  - 심층 토론         - 결과 수집
       │                    │
       └────────────────────┘
                │
                ▼
       [Data Collector]
  - CollectorNode → httpx
  - 적법성 검증
  - 데이터 수집
```

## 구현 내용

### 7-1. Config 변경

- `backend/shared/config.py`: `DATA_COLLECTOR_URL` 설정 추가 (기본값: `http://localhost:8001`)

### 7-2. SessionManager

- **파일**: `backend/gateway/session_manager.py`
- conversation_id별 DiscussionEngine 인스턴스 관리
- OrderedDict 기반 LRU 캐시 (최대 500 세션)
- 모듈 레벨 싱글턴 인스턴스

### 7-3. WebSocket 핸들러 통합

- **파일**: `backend/gateway/routes/chat.py`
- Echo 블록을 DiscussionEngine + PipelineOrchestrator 호출로 교체
- 응답 타입별 라우팅:
  - `clarification`: 명확화 질문 전달
  - `designs_presented`: 설계안 목록 전달
  - `critique_complete`: 비평 결과 전달
  - `plan_generated`: 파이프라인 실행 트리거
  - `security_warning`: 보안 경고
  - `error`: 에러 메시지
- 파이프라인 실시간 상태 스트리밍 (`on_status` → WebSocket)
- 메시지 DB 저장 (user + assistant)

### 7-4. CollectorNode HTTP 통합

- **파일**: `backend/pipeline/agents/collector.py`
- Data Collector API 4단계 호출: create → compliance → collect → data
- 적법성 차단 시 에러 반환
- httpx 에러 처리 (ConnectError → LLM fallback, Timeout/HTTPError → 실패)
- source_url 없으면 기존 LLM 기반 fallback 유지

### 7-5. Conversation Routes 인증

- **파일**: `backend/gateway/routes/conversations.py`
- 모든 엔드포인트에 `get_current_user` 의존성 추가
- 소유권 기반 필터링 (자신의 대화만 조회 가능)
- `ConversationCreate`에서 `user_id` 필드 제거 (인증에서 자동 제공)

### 7-6. Docker Compose

- **파일**: `docker/docker-compose.yml`
- `data-collector` 서비스 추가 (포트 8001)
- backend 환경변수에 `DATA_COLLECTOR_URL` 추가

### 7-7. Frontend 메시지 타입 처리

- **파일**: `frontend/app/components/ChatWindow.tsx`
- WebSocket URL에 인증 토큰 추가 (`?token=`)
- `onmessage` 핸들러: 메시지 타입별 switch 처리
- `formatDiscussionMessage()` 함수: 설계안/비평/질문 포맷팅
- 파이프라인 이벤트 표시 (시작, 에이전트 완료, 결과)

## WebSocket 메시지 타입

### 클라이언트 → 서버

| 타입 | 필드 | 설명 |
|------|------|------|
| (메시지) | `content`, `conversation_id` | 사용자 메시지 |

### 서버 → 클라이언트

| 타입 | 발생 시점 | 주요 필드 |
|------|----------|----------|
| `user_message_received` | 메시지 수신 확인 | `content` |
| `clarification` | 모호한 입력 | `content`, `questions` |
| `designs_presented` | 설계안 생성 완료 | `content`, `designs` |
| `critique_complete` | 비평 완료 | `content`, `critiques` |
| `plan_generated` | 계획 확정 | `content`, `selected_design` |
| `pipeline_started` | 파이프라인 실행 시작 | `design_name`, `agent_count` |
| `agent_completed` | 에이전트 완료 | `agent_name`, `status`, `duration` |
| `pipeline_result` | 파이프라인 완료 | `content`, `result` |
| `pipeline_failed` | 파이프라인 실패 | `reason` |
| `security_warning` | 보안 위험 감지 | `content` |
| `error` | 에러 발생 | `content` |

## API 변경사항

### Conversations API (인증 추가)

모든 엔드포인트에 `Authorization: Bearer <token>` 헤더 필수:

| 메서드 | 경로 | 변경 |
|--------|------|------|
| POST | `/api/v1/conversations` | 인증 필수, `user_id` 요청 필드 제거 |
| GET | `/api/v1/conversations` | 인증 필수, 본인 대화만 반환 |
| GET | `/api/v1/conversations/{id}` | 인증 필수, 소유권 검증 |

## 테스트

### 단위 테스트

| 파일 | 대상 | 테스트 수 |
|------|------|----------|
| `test_session_manager.py` | SessionManager LRU 캐시 | 7 |
| `test_collector_integration.py` | CollectorNode HTTP/fallback | 7 |
| `test_conversations.py` | Conversations 인증 | 7 |

### E2E 테스트

| 파일 | 대상 | 테스트 수 |
|------|------|----------|
| `test_full_flow.py` | 전체 Discussion→Pipeline 흐름 | 8 |

## 알려진 제한사항

1. **파이프라인 블로킹**: WebSocket 핸들러 내에서 파이프라인이 동기 실행됨 (최대 5분). 향후 백그라운드 태스크로 분리 가능.
2. **세션 메모리**: SessionManager가 인메모리 → 서버 재시작 시 세션 초기화. 프로덕션에서는 Redis 기반 필요.
3. **프론트엔드 인증**: localStorage 기반 토큰 관리. 프로덕션에서는 NextAuth.js 세션 연동 필요.
4. **Data Collector 연결**: ConnectError 시 LLM fallback. 프로덕션에서는 재시도 + circuit breaker 필요.
5. **메시지 저장 실패**: DB 저장 실패 시 로그만 남김 (사용자 경험 중단 안 함).

## 다음 단계

- **Phase 2C**: API 키 관리 + 비용 Circuit Breaker
- **Phase 8**: 개발자 고급 모드 (React Flow 기반 파이프라인 빌더)
- develop → main PR: 전체 E2E 검증 후 생성
