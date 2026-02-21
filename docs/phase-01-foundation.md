# Phase 1: 프로젝트 기반 구조 및 챗봇 기본 UI

## 개요

Phase 1은 AgentForge의 기반 인프라를 구축합니다. AgentForge는 한국어 네이티브 멀티 에이전트 플랫폼으로, 이 단계에서는 실시간 WebSocket 통신, 영속적인 대화 저장, 그리고 컨테이너화된 개발 환경을 갖춘 작동하는 챗봇 인터페이스를 제공합니다.

**목표:**
- 프론트엔드, 백엔드, 데이터 수집기 서비스를 위한 모노레포 구조 설정
- 실시간 메시징이 가능한 기본 챗봇 UI 구현
- 대화 및 메시지 관리를 위한 REST API 생성
- PostgreSQL을 사용한 데이터베이스 영속성 구축
- 로컬 개발을 위한 Docker Compose 구성
- 자동화된 테스트 및 린팅을 포함한 CI/CD 파이프라인 설정

**산출물:**
- http://localhost:3000 에서 접근 가능한 기능적 채팅 인터페이스
- http://localhost:8000 에서 제공되는 WebSocket 지원 RESTful API
- 핫 리로드 기능을 갖춘 컨테이너화된 개발 환경
- 자동화된 테스트 및 코드 품질 검사
- 완전한 프로젝트 문서

## 아키텍처

Phase 1은 전체 AgentForge 아키텍처의 단순화된 버전을 구현하며, 핵심 통신 인프라에 중점을 둡니다.

### 기술 스택

| 계층 | 기술 | 목적 |
|------|------|------|
| **프론트엔드** | Next.js 14+ (App Router) | 서버 컴포넌트를 갖춘 현대적인 React 프레임워크 |
| **UI 프레임워크** | Tailwind CSS | 빠른 개발을 위한 유틸리티 우선 CSS |
| **백엔드** | FastAPI | 고성능 비동기 Python 웹 프레임워크 |
| **데이터베이스** | PostgreSQL 16 | 구조화된 데이터를 위한 관계형 데이터베이스 |
| **캐시** | Redis 7 | 세션 및 실시간 데이터를 위한 인메모리 캐시 |
| **ORM** | SQLAlchemy 2.0+ (Async) | 타입 안전 데이터베이스 작업 |
| **WebSocket** | FastAPI WebSocket | 실시간 양방향 통신 |
| **컨테이너** | Docker Compose | 로컬 개발 환경 오케스트레이션 |
| **CI/CD** | GitHub Actions | 자동화된 테스트, 린팅 및 코드 리뷰 |

### 시스템 구성 요소

```
┌─────────────────┐
│   브라우저      │
│  (Next.js UI)   │
└────────┬────────┘
         │ HTTP/WS
         │
┌────────▼────────┐
│   API Gateway   │
│   (FastAPI)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ PostgreSQL │ │  Redis  │
│   (영속성)  │ │ (캐시)  │
└───────────┘ └─────────┘
```

**데이터 흐름:**
1. 사용자가 Next.js 프론트엔드에서 WebSocket을 통해 메시지 전송
2. FastAPI 백엔드가 메시지를 수신하고 PostgreSQL에 저장
3. 백엔드가 메시지 처리 (Phase 1: echo 응답; 이후 단계: LLM 처리)
4. WebSocket 연결을 통해 응답 전송
5. 프론트엔드가 실시간으로 새 메시지로 UI 업데이트

## 디렉토리 구조

```
AgentForge/
├── .github/
│   └── workflows/               # CI/CD 파이프라인
│       ├── test.yml            # 자동화된 테스트
│       ├── lint.yml            # 코드 품질 검사
│       └── claude-code-review.yml  # AI 기반 코드 리뷰
│
├── frontend/                    # Next.js 프론트엔드 애플리케이션
│   ├── src/
│   │   ├── app/                # Next.js App Router
│   │   │   ├── page.tsx       # 채팅 인터페이스가 있는 홈 페이지
│   │   │   ├── layout.tsx     # 루트 레이아웃
│   │   │   └── globals.css    # 전역 스타일
│   │   ├── components/         # React 컴포넌트
│   │   │   ├── ChatWindow.tsx # 메인 채팅 인터페이스
│   │   │   ├── MessageBubble.tsx  # 개별 메시지 표시
│   │   │   └── MessageInput.tsx   # 메시지 입력 필드
│   │   └── lib/                # 유틸리티 및 훅
│   │       └── websocket.ts   # 재연결 기능이 있는 WebSocket 클라이언트
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
│
├── backend/                     # FastAPI 백엔드 서비스
│   ├── shared/                  # 공유 모델 및 유틸리티
│   │   ├── models.py           # SQLAlchemy ORM 모델
│   │   ├── schemas.py          # Pydantic 검증 스키마
│   │   ├── database.py         # 데이터베이스 연결 및 세션
│   │   └── config.py           # 구성 관리
│   ├── api_gateway/             # API Gateway 서비스 (Phase 1 중점)
│   │   ├── main.py             # FastAPI 애플리케이션 진입점
│   │   ├── routes/             # API 라우트 핸들러
│   │   │   ├── health.py      # 헬스 체크 엔드포인트
│   │   │   ├── conversations.py  # 대화 CRUD
│   │   │   └── websocket.py   # WebSocket 채팅 핸들러
│   │   └── dependencies.py     # 의존성 주입
│   ├── discussion_engine/       # (Phase 2+)
│   ├── pipeline_orchestrator/   # (Phase 3+)
│   └── requirements.txt
│
├── data-collector/              # (Phase 4+)
│   └── requirements.txt
│
├── docker/                      # Docker 구성
│   ├── docker-compose.yml      # 서비스 오케스트레이션
│   ├── Dockerfile.frontend     # 프론트엔드 컨테이너
│   ├── Dockerfile.backend      # 백엔드 컨테이너
│   ├── Dockerfile.collector    # 데이터 수집기 컨테이너 (Phase 4+)
│   └── .env.example            # 환경 변수 템플릿
│
├── tests/                       # 테스트 스위트
│   ├── unit/                   # 유닛 테스트
│   ├── integration/            # 통합 테스트
│   └── e2e/                    # 엔드투엔드 테스트
│
├── docs/                        # 문서
│   ├── phase-01-foundation.md  # 이 문서
│   ├── architecture.md         # 시스템 아키텍처 (예정)
│   └── api-reference.md        # API 문서 (예정)
│
└── README.md                    # 프로젝트 개요
```

## 데이터베이스 스키마

Phase 1은 사용자 관리 및 대화 영속성을 위한 세 가지 핵심 테이블을 구현합니다.

### Users 테이블

역할 기반 접근 제어 기반을 갖춘 사용자 계정을 저장합니다.

| 컬럼 | 타입 | 제약 조건 | 설명 |
|------|------|----------|------|
| `id` | UUID | PRIMARY KEY | 고유 사용자 식별자 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 사용자 이메일 주소 |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt 해시 비밀번호 |
| `display_name` | VARCHAR(100) | NOT NULL | 사용자 표시 이름 (한글 지원) |
| `role` | ENUM | NOT NULL, DEFAULT 'free' | 사용자 역할 (free, pro, admin) |
| `created_at` | TIMESTAMP | NOT NULL | 계정 생성 타임스탬프 |
| `updated_at` | TIMESTAMP | NOT NULL | 마지막 업데이트 타임스탬프 |

**인덱스:**
- 기본 키: `id`
- 고유: `email`

**참고 사항:**
- Phase 1: 비밀번호 해싱 구현, Phase 2에서 인증
- `display_name`의 UTF-8 인코딩을 통한 한글 문자 지원

### Conversations 테이블

사용자와 AI 시스템 간의 대화 세션을 저장합니다.

| 컬럼 | 타입 | 제약 조건 | 설명 |
|------|------|----------|------|
| `id` | UUID | PRIMARY KEY | 고유 대화 식별자 |
| `user_id` | UUID | FOREIGN KEY (users.id), NOT NULL | 대화 소유자 |
| `title` | VARCHAR(255) | NOT NULL | 대화 제목 (자동 생성 또는 사용자 설정) |
| `status` | ENUM | NOT NULL, DEFAULT 'active' | 대화 상태 (active, archived) |
| `created_at` | TIMESTAMP | NOT NULL | 대화 시작 타임스탬프 |
| `updated_at` | TIMESTAMP | NOT NULL | 마지막 메시지 타임스탬프 |

**인덱스:**
- 기본 키: `id`
- 외래 키: `user_id` (CASCADE DELETE)
- 인덱스: `user_id, status` (빠른 사용자 대화 쿼리를 위해)

**참고 사항:**
- 제목은 한글 문자 지원
- 아카이빙은 삭제 없이 대화 기록 보존

### Messages 테이블

대화 내의 개별 메시지를 저장합니다.

| 컬럼 | 타입 | 제약 조건 | 설명 |
|------|------|----------|------|
| `id` | UUID | PRIMARY KEY | 고유 메시지 식별자 |
| `conversation_id` | UUID | FOREIGN KEY (conversations.id), NOT NULL | 상위 대화 |
| `role` | ENUM | NOT NULL | 메시지 역할 (user, assistant, system) |
| `content` | TEXT | NOT NULL | 메시지 내용 (한글 지원) |
| `metadata_` | JSONB | NULLABLE | 추가 메타데이터 (타임스탬프, 모델 정보 등) |
| `created_at` | TIMESTAMP | NOT NULL | 메시지 생성 타임스탬프 |

**인덱스:**
- 기본 키: `id`
- 외래 키: `conversation_id` (CASCADE DELETE)
- 인덱스: `conversation_id, created_at` (시간순 메시지 검색을 위해)

**참고 사항:**
- 확장성을 위한 JSONB 메타데이터 (토큰 수, 모델 버전 등)
- `content` 필드의 완전한 한글 지원

### 엔티티 관계

```
users (1) ──< (N) conversations ──< (N) messages
```

- 한 명의 사용자는 여러 대화를 가질 수 있음
- 한 대화는 여러 메시지를 가질 수 있음
- 계단식 삭제: 사용자 삭제 시 모든 대화 및 메시지 제거
- 계단식 삭제: 대화 삭제 시 모든 메시지 제거

## API 엔드포인트

Phase 1은 실시간 채팅을 위한 WebSocket 지원과 함께 RESTful API를 구현합니다.

### 헬스 체크

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| `GET` | `/api/v1/health` | 시스템 헬스 및 버전 체크 | 아니오 |

**응답:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 대화 관리

#### 대화 생성

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| `POST` | `/api/v1/conversations` | 새 대화 생성 | 아니오 (Phase 2: 예) |

**요청 본문:**
```json
{
  "title": "새 채팅 세션",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"  // Phase 1에서는 선택적
}
```

**응답 (201 Created):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "새 채팅 세션",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### 대화 목록 조회

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| `GET` | `/api/v1/conversations?user_id={uuid}` | 사용자의 모든 대화 목록 조회 | 아니오 (Phase 2: 예) |

**쿼리 파라미터:**
- `user_id` (UUID): 사용자 ID로 필터링
- `status` (선택): 상태로 필터링 (active, archived)
- `limit` (선택): 결과 수 (기본값: 20, 최대: 100)
- `offset` (선택): 페이지네이션 오프셋 (기본값: 0)

**응답 (200 OK):**
```json
{
  "conversations": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "에이전트에 대한 채팅",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### 대화 상세 조회

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| `GET` | `/api/v1/conversations/{conversation_id}` | 메시지 기록과 함께 대화 조회 | 아니오 (Phase 2: 예) |

**응답 (200 OK):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "에이전트에 대한 채팅",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "messages": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "role": "user",
      "content": "안녕하세요, 어떻게 지내세요?",
      "created_at": "2024-01-15T10:30:15Z"
    },
    {
      "id": "770e8400-e29b-41d4-a716-446655440003",
      "role": "assistant",
      "content": "안녕하세요! 잘 지내고 있습니다. 오늘 어떻게 도와드릴까요?",
      "created_at": "2024-01-15T10:30:18Z"
    }
  ]
}
```

### WebSocket 채팅

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| `WS` | `/api/v1/ws/chat/{conversation_id}` | 실시간 채팅 WebSocket 연결 | 아니오 (Phase 2: 예) |

**연결:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/chat/${conversationId}`);
```

**클라이언트 → 서버 메시지:**
```json
{
  "type": "user_message",
  "content": "무엇을 할 수 있나요?",
  "timestamp": "2024-01-15T10:30:20Z"
}
```

**서버 → 클라이언트 메시지:**
```json
{
  "type": "assistant_message",
  "content": "다양한 작업을 도와드릴 수 있습니다...",
  "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T10:30:22Z"
}
```

**상태 메시지:**
```json
{
  "type": "status",
  "content": "대화에 연결됨",
  "timestamp": "2024-01-15T10:30:19Z"
}
```

**에러 처리:**
- WebSocket 연결 끊김: 클라이언트가 지수 백오프로 자동 재연결
- 잘못된 메시지: 서버가 에러 타입 메시지 전송
- 연결 제한: 대화당 최대 100개의 동시 연결

## 프론트엔드 컴포넌트

### ChatWindow 컴포넌트

WebSocket 연결 및 메시지 표시를 관리하는 메인 채팅 인터페이스 컴포넌트입니다.

**위치:** `frontend/src/components/ChatWindow.tsx`

**기능:**
- 자동 재연결 기능이 있는 WebSocket 연결 관리
- 실시간 메시지 스트리밍
- 새 메시지 시 하단으로 스크롤
- 로딩 상태 및 에러 처리
- 적절한 폰트 렌더링으로 한글 텍스트 지원

**Props:**
```typescript
interface ChatWindowProps {
  conversationId: string;
  onError?: (error: Error) => void;
}
```

**상태 관리:**
- 메시지 배열 (사용자 및 어시스턴트 메시지)
- 연결 상태 (connecting, connected, disconnected, error)
- 메시지 전송을 위한 로딩 상태
- 메시지 컨테이너를 위한 자동 스크롤 참조

### MessageBubble 컴포넌트

역할 기반 스타일링이 있는 개별 메시지 표시 컴포넌트입니다.

**위치:** `frontend/src/components/MessageBubble.tsx`

**기능:**
- 역할 기반 스타일링 (user: 파란색, assistant: 회색)
- 타임스탬프 표시
- Markdown 렌더링 지원 (Phase 2+)
- 한글 텍스트 줄 바꿈 및 줄 넘김

**Props:**
```typescript
interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}
```

### MessageInput 컴포넌트

전송 버튼 및 키보드 단축키가 있는 메시지 입력 필드입니다.

**위치:** `frontend/src/components/MessageInput.tsx`

**기능:**
- 자동 확장 텍스트 영역
- Enter로 전송 (Shift+Enter로 새 줄)
- 문자 제한 표시기 (선택)
- 한글 IME (입력기) 지원
- 메시지 전송 중 비활성화 상태

**Props:**
```typescript
interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}
```

### WebSocket 클라이언트 유틸리티

재연결 로직이 있는 재사용 가능한 WebSocket 클라이언트입니다.

**위치:** `frontend/src/lib/websocket.ts`

**기능:**
- 지수 백오프를 사용한 자동 재연결
- 연결 상태 관리
- 타입 안전 메시지 처리
- 에러 복구 및 재시도 로직
- 연결 상태 확인을 위한 하트비트/핑퐁

**사용법:**
```typescript
const client = new WebSocketClient(`ws://localhost:8000/api/v1/ws/chat/${id}`);

client.onMessage((message) => {
  console.log('수신:', message);
});

client.onError((error) => {
  console.error('WebSocket 에러:', error);
});

client.connect();
```

## Docker 서비스

Phase 1은 Docker Compose를 사용하여 로컬 개발을 위한 모든 서비스를 오케스트레이션합니다.

### 서비스 구성

| 서비스 | 이미지 | 포트 | 목적 |
|---------|-------|------|------|
| `frontend` | Custom (Node 20) | 3000 | Next.js 개발 서버 |
| `backend` | Custom (Python 3.11) | 8000 | FastAPI 애플리케이션 |
| `postgres` | postgres:16-alpine | 5432 | PostgreSQL 데이터베이스 |
| `redis` | redis:7-alpine | 6379 | Redis 캐시 |
| `pgadmin` | dpage/pgadmin4 | 5050 | 데이터베이스 관리 UI (선택) |

### Docker Compose 구성

**위치:** `docker/docker-compose.yml`

**주요 기능:**
- 프론트엔드 및 백엔드 모두 핫 리로드
- 소스 코드를 위한 볼륨 마운트
- 모든 서비스에 대한 헬스 체크
- 의존성 순서 (백엔드는 postgres + redis 대기)
- `.env` 파일을 통한 환경 변수 구성

**서비스 세부 정보:**

#### 프론트엔드 서비스
- 베이스: `node:20-alpine`
- 작업 디렉토리: `/app`
- 명령: `npm run dev`
- 볼륨: `./frontend:/app`, `node_modules` 캐시
- 환경: `NEXT_PUBLIC_API_URL=http://localhost:8000`

#### 백엔드 서비스
- 베이스: `python:3.11-slim`
- 작업 디렉토리: `/app`
- 명령: `uvicorn api_gateway.main:app --host 0.0.0.0 --reload`
- 볼륨: `./backend:/app`
- 환경: 데이터베이스 URL, Redis URL, API 키
- 의존성: `postgres`, `redis`

#### PostgreSQL 서비스
- 베이스: `postgres:16-alpine`
- 볼륨: `pgdata:/var/lib/postgresql/data`
- 환경: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- 헬스 체크: `pg_isready`

#### Redis 서비스
- 베이스: `redis:7-alpine`
- 볼륨: `redisdata:/data`
- 헬스 체크: `redis-cli ping`

### 환경 변수

**위치:** `docker/.env.example`

필수 변수:
```bash
# 데이터베이스
POSTGRES_DB=agentforge
POSTGRES_USER=agentforge
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://redis:6379

# 백엔드
DATABASE_URL=postgresql+asyncpg://agentforge:your_secure_password@postgres:5432/agentforge
SECRET_KEY=your_secret_key_here

# API 키 (Phase 2+)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
NAVER_API_KEY=...
```

## 로컬 실행 방법

### 사전 요구 사항

- Docker 24.0+ 및 Docker Compose 2.20+
- Git

### 단계별 설정

1. **리포지토리 클론:**
```bash
git clone https://github.com/Maroco0109/AgentForge.git
cd AgentForge
```

2. **환경 변수 구성:**
```bash
cd docker
cp .env.example .env
# .env를 편집하여 비밀번호 및 API 키 설정
```

3. **모든 서비스 시작:**
```bash
docker-compose up -d
```

4. **서비스 실행 확인:**
```bash
docker-compose ps
```

예상 출력:
```
NAME                STATUS    PORTS
agentforge-frontend-1   running   0.0.0.0:3000->3000/tcp
agentforge-backend-1    running   0.0.0.0:8000->8000/tcp
agentforge-postgres-1   running   0.0.0.0:5432->5432/tcp
agentforge-redis-1      running   0.0.0.0:6379->6379/tcp
```

5. **데이터베이스 초기화:**
```bash
docker-compose exec backend python -m alembic upgrade head
```

6. **애플리케이션 접속:**
- 프론트엔드: http://localhost:3000
- 백엔드 API: http://localhost:8000
- API 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/api/v1/health

### 개발 워크플로우

**핫 리로드:**
- 프론트엔드: `frontend/src/**` 변경 시 자동 재빌드 트리거
- 백엔드: `backend/**/*.py` 변경 시 uvicorn 리로드 트리거

**로그 보기:**
```bash
# 모든 서비스
docker-compose logs -f

# 특정 서비스
docker-compose logs -f backend
docker-compose logs -f frontend
```

**데이터베이스 접속:**
```bash
# psql 클라이언트
docker-compose exec postgres psql -U agentforge -d agentforge

# pgAdmin (활성화된 경우)
# http://localhost:5050 열기
# .env의 자격 증명으로 로그인
```

**서비스 중지:**
```bash
# 컨테이너 제거 없이 중지
docker-compose stop

# 컨테이너 중지 및 제거 (볼륨은 보존)
docker-compose down

# 볼륨 포함 모든 것 중지 및 제거
docker-compose down -v
```

## 테스트

Phase 1은 기본 테스트 인프라를 포함합니다.

### 테스트 구성

```
tests/
├── unit/                      # 유닛 테스트 (빠름, 격리됨)
│   ├── test_models.py        # 데이터베이스 모델 테스트
│   ├── test_schemas.py       # Pydantic 스키마 검증 테스트
│   └── test_websocket.py     # WebSocket 핸들러 유닛 테스트
│
├── integration/               # 통합 테스트 (데이터베이스, API)
│   ├── test_api_conversations.py  # 대화 CRUD 테스트
│   ├── test_websocket_chat.py     # WebSocket 통합 테스트
│   └── test_database.py      # 데이터베이스 작업 테스트
│
└── e2e/                       # 엔드투엔드 테스트 (Phase 2+)
    └── test_chat_flow.py     # 전체 채팅 플로우 테스트
```

### 테스트 실행

**백엔드 테스트:**
```bash
# 모든 백엔드 테스트 실행
docker-compose exec backend pytest tests/ -v

# 커버리지 포함 실행
docker-compose exec backend pytest tests/ --cov=backend --cov-report=html

# 특정 테스트 파일 실행
docker-compose exec backend pytest tests/unit/test_models.py -v
```

**프론트엔드 테스트 (Phase 2+):**
```bash
# Jest 테스트 실행
docker-compose exec frontend npm test

# 커버리지 포함 실행
docker-compose exec frontend npm test -- --coverage
```

### 테스트 데이터베이스

테스트는 개발 데이터 오염을 피하기 위해 별도의 테스트 데이터베이스를 사용합니다.

**구성:**
- 데이터베이스: `agentforge_test`
- 테스트 스위트 후 자동 정리
- 공통 테스트 데이터를 위한 픽스처

**테스트 예시:**
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import User, Conversation
from backend.shared.database import get_db

@pytest.mark.asyncio
async def test_create_conversation(db_session: AsyncSession):
    # 테스트 사용자 생성
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        display_name="테스트 사용자"
    )
    db_session.add(user)
    await db_session.commit()

    # 대화 생성
    conversation = Conversation(
        user_id=user.id,
        title="테스트 대화"
    )
    db_session.add(conversation)
    await db_session.commit()

    # 검증
    assert conversation.id is not None
    assert conversation.status == ConversationStatus.ACTIVE
```

## CI/CD 파이프라인

### GitHub Actions 워크플로우

**위치:** `.github/workflows/`

#### 1. 테스트 워크플로우 (`test.yml`)

**트리거:**
- 모든 pull request
- `main` 및 `develop` 브랜치에 대한 push

**작업:**
- `backend-test`: PostgreSQL 및 Redis 서비스와 함께 pytest 실행
- `frontend-build`: Next.js 빌드 성공 확인

**환경:**
- PostgreSQL 16 (테스트 데이터베이스)
- Redis 7
- Python 3.11
- Node.js 20

#### 2. 린트 워크플로우 (`lint.yml`)

**트리거:**
- 모든 pull request
- `main` 및 `develop` 브랜치에 대한 push

**작업:**
- `backend-lint`: Ruff (빠른 Python linter/formatter) 실행
- `frontend-lint`: Next.js 구성으로 ESLint 실행

**품질 게이트:**
- 통과하려면 린팅 에러 0개 필요
- 코드 포맷팅 자동 검사

#### 3. Claude Code Review (`claude-code-review.yml`)

**트리거:**
- Pull request 열림 또는 업데이트됨
- `main` 또는 `develop` 브랜치를 대상으로 함

**중점 영역:**
- 보안 취약점 (OWASP Top 10)
- 프롬프트 주입 위험 (LLM 특화)
- 코드 품질 및 에러 처리
- 테스트 커버리지 격차
- 성능 문제 (N+1 쿼리 등)

**AI 리뷰 범위:**
- 중요: 보안, 버그, 데이터 유출
- 중요: 코드 품질, 테스트 커버리지
- 에이전트 특화: LLM 안전성, 비용 효율성

### 필수 시크릿

GitHub 리포지토리 설정에서 구성:

| 시크릿 | 목적 | 필요한 대상 |
|--------|------|-------------|
| `ANTHROPIC_API_KEY` | Claude Code Review | CI/CD |
| `OPENAI_API_KEY` | LLM 기능 (Phase 2+) | 배포 |
| `DATABASE_URL` | 프로덕션 데이터베이스 | 배포 |

## 한국어 지원

Phase 1은 완전한 한국어 지원을 포함합니다.

### 데이터베이스 구성
- 모든 텍스트 필드에 UTF-8 인코딩
- 한국어 정렬을 위한 적절한 콜레이션
- 텍스트 필드가 한글 문자 지원

### 프론트엔드 구성
- 한국어 웹 폰트 (Noto Sans KR, Pretendard)
- 한국어 텍스트에 적절한 줄 바꿈
- 텍스트 입력에서 IME (입력기) 지원
- 혼합 콘텐츠를 위한 오른쪽에서 왼쪽 텍스트 처리

### 한국어 텍스트 처리 예시
```typescript
// 한글 문자 감지
const hasKorean = /[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]/.test(text);

// 한국어 특화 줄 바꿈 적용
<p className="break-words whitespace-pre-wrap lang-ko">
  {koreanText}
</p>
```

## 성능 고려 사항

Phase 1은 성능 기준을 확립합니다.

### 데이터베이스
- 빠른 조인을 위한 외래 키 인덱싱
- 연결 풀링 (SQLAlchemy async engine)
- 대화 목록을 위한 쿼리 최적화

### WebSocket
- 연결 제한: 대화당 동시 100개
- 메시지 속도 제한: 사용자당 초당 10개 메시지
- 지수 백오프를 사용한 자동 재연결

### 프론트엔드
- 초기 렌더링을 위한 React Server Components
- 실시간 업데이트를 위한 클라이언트 측 상태
- 대화 기록을 위한 지연 로딩

### 모니터링 (Phase 2+)
- 응답 시간 추적
- 에러 율 모니터링
- WebSocket 연결 메트릭

## 보안 기준

Phase 1은 보안 기반을 확립합니다.

### 현재 구현
- 환경 변수 구성 (하드코딩된 시크릿 없음)
- API 엔드포인트를 위한 CORS 구성
- Pydantic 스키마를 통한 입력 검증
- SQL 주입 보호 (SQLAlchemy ORM)

### Phase 2 추가 사항
- JWT 인증
- bcrypt를 사용한 비밀번호 해싱
- 사용자당 속도 제한
- CSRF 보호
- Content Security Policy 헤더

## 알려진 제한 사항

Phase 1은 의도적으로 범위가 제한됩니다:

1. **인증 없음:** 사용자 ID 수동 지정 (Phase 2에서 추가)
2. **LLM 통합 없음:** Echo 응답만 (Phase 2에서 추가)
3. **파일 업로드 없음:** 텍스트 전용 메시지 (Phase 3에서 추가)
4. **멀티 에이전트 파이프라인 없음:** 단일 대화 스레드 (Phase 3에서 추가)
5. **프로덕션 배포 없음:** Docker Compose만 (Phase 5에서 Kubernetes)

## 성공 기준

Phase 1은 다음 조건을 만족하면 완료됩니다:

- [ ] 모든 Docker 서비스가 성공적으로 시작됨
- [ ] http://localhost:3000 에서 프론트엔드 접속 가능
- [ ] 백엔드 헬스 체크가 200 OK 반환
- [ ] 대화 생성 API 엔드포인트 작동
- [ ] 대화 목록 조회 API 엔드포인트 작동
- [ ] WebSocket 연결 확립됨
- [ ] 실시간으로 메시지 전송 및 수신됨
- [ ] PostgreSQL에 메시지 영속화됨
- [ ] 모든 백엔드 테스트 통과
- [ ] 프론트엔드가 에러 없이 빌드됨
- [ ] GitHub에서 CI/CD 파이프라인 통과
- [ ] 문서가 완전하고 정확함

## 다음 단계

### Phase 2: 인증 및 인가
- 프론트엔드를 위한 NextAuth.js v5 구현
- 백엔드에 JWT 인증 추가
- 사용자 등록 및 로그인 플로우
- 역할 기반 접근 제어 (RBAC)
- 안전한 대화 접근 (사용자는 자신의 대화만 볼 수 있음)

### Phase 3: LLM 통합
- OpenAI API 통합
- Anthropic Claude API 통합
- 멀티 LLM 라우팅 로직
- WebSocket을 통한 스트리밍 응답
- 토큰 사용량 추적

### Phase 4: Discussion Engine
- 사용자 프롬프트에서 의도 분석
- 멀티 라운드 디자인 대화 (3-5 라운드)
- 디자인 비평 및 반복
- 계획 승인 워크플로우

### Phase 5: Pipeline Orchestrator
- LangGraph 통합
- 동적 에이전트 파이프라인 구성
- 멀티 에이전트 조정
- 에이전트 간 상태 관리

## 문제 해결

### 일반적인 문제

**문제: Docker 컨테이너 시작 실패**
```bash
# 로그 확인
docker-compose logs

# 이미지 재빌드
docker-compose build --no-cache
docker-compose up -d
```

**문제: 프론트엔드가 백엔드에 연결할 수 없음**
- 프론트엔드 `.env.local`에서 `NEXT_PUBLIC_API_URL` 확인
- 백엔드의 CORS 구성 확인
- 백엔드가 실행 중인지 확인: `docker-compose ps`

**문제: 데이터베이스 연결 에러**
- PostgreSQL이 실행 중인지 확인: `docker-compose ps postgres`
- `docker/.env`의 자격 증명 확인
- `DATABASE_URL` 형식 확인: `postgresql+asyncpg://user:pass@host:port/db`

**문제: WebSocket 연결 실패**
- 대화 ID가 유효한 UUID인지 확인
- 백엔드 WebSocket 엔드포인트 확인: `ws://localhost:8000/api/v1/ws/chat/{id}`
- 브라우저 콘솔에서 에러 확인

**문제: 테스트 실패**
```bash
# 테스트 데이터베이스 초기화
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head

# 상세 출력으로 테스트 실행
docker-compose exec backend pytest tests/ -vv
```

## 참고 자료

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL 16 문서](https://www.postgresql.org/docs/16/)
- [Docker Compose 참조](https://docs.docker.com/compose/)

## 변경 로그

### v0.1.0 (Phase 1 - 2024-01-15)
- 초기 프로젝트 설정
- WebSocket을 사용한 기본 챗봇 UI
- 대화를 위한 REST API
- PostgreSQL 데이터베이스 스키마
- Docker Compose 개발 환경
- GitHub Actions를 사용한 CI/CD 파이프라인
- 한국어 지원
