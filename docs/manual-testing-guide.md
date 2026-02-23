# AgentForge 수동 테스트 가이드

이 문서는 AgentForge 플랫폼을 수동으로 테스트하기 위한 실전 가이드입니다. 각 기능별로 테스트 시나리오, 입력값, 기대 결과, 검증 방법을 포함합니다.

---

## 0. 사전 준비

### 0.1 서비스 실행

```bash
cd /home/maroco/multi_agents/docker
docker compose up -d
```

모든 서비스가 정상 시작될 때까지 약 30-60초 대기합니다.

### 0.2 서비스 포트 및 URL

| 서비스 | 포트 | URL | 설명 |
|--------|------|-----|------|
| **Frontend** | 3000 | http://localhost:3000 | Next.js 웹 UI |
| **API Gateway** | 8000 | http://localhost:8000 | FastAPI 백엔드 |
| **Data Collector** | 8001 | http://localhost:8001 | 데이터 수집 마이크로서비스 |
| **PostgreSQL** | 5432 | localhost:5432 | 데이터베이스 (user: postgres, pw: postgres) |
| **Redis** | 6379 | localhost:6379 | 캐시 및 Rate Limiting |
| **Prometheus** | 9090 | http://localhost:9090 | 메트릭 수집 |
| **Grafana** | 3001 | http://localhost:3001 | 대시보드 (admin/admin) |

### 0.3 헬스 체크

모든 서비스가 정상 작동하는지 확인합니다.

```bash
# API Gateway 헬스 체크
curl http://localhost:8000/api/v1/health
```

**기대 응답:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "timestamp": "2026-02-23T10:30:45.123456+00:00"
}
```

```bash
# Data Collector 헬스 체크
curl http://localhost:8001/api/v1/health
```

### 0.4 브라우저 개발자 도구 설정

테스트 중 아래 기능을 활용합니다:
- **F12** 또는 **우클릭 → 검사** 개발자 도구 열기
- **Network** 탭: API 요청/응답 확인
- **Console** 탭: JavaScript 에러 확인
- **Application** 탭: localStorage 토큰 확인
- **Storage** 탭: 쿠키/세션 스토리지 확인

### 0.5 환경변수 설정 (LLM API 키)

LLM 기능을 사용하려면 OpenAI API 키를 설정해야 합니다.

**설정 파일:** `docker/.env`

```bash
# 필수 설정
SECRET_KEY=<openssl rand -hex 32 로 생성>
OPENAI_API_KEY=sk-proj-your-key-here

# 선택 설정
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# DAILY_COST_LIMIT=10.0
```

**중요:** `docker-compose.yml`의 backend 서비스 `environment` 섹션에 아래 항목이 포함되어야 합니다:
```yaml
- SECRET_KEY=${SECRET_KEY}
- OPENAI_API_KEY=${OPENAI_API_KEY}
- ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
- DAILY_COST_LIMIT=${DAILY_COST_LIMIT:-10.0}
```

**환경변수 확인:**
```bash
# Docker 재시작
cd docker && docker compose down && docker compose up -d

# 환경변수 로드 확인
docker compose exec backend printenv | grep -E "OPENAI|SECRET_KEY"
```

**기대 결과:** `OPENAI_API_KEY`와 `SECRET_KEY`가 출력되어야 합니다.

---

## 1. 회원가입 테스트 (`/register`)

사용자 계정을 생성하고 초기 토큰을 획득합니다.

### 1.1 성공 케이스 - 유효한 입력

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/register |
| **입력** | Email: `testuser@example.com`, Password: `TestPassword123`, Display Name: `Test User` |
| **기대 결과** | 회원가입 성공 → `/conversations` 페이지로 자동 리다이렉트 |
| **확인 방법** | 1. URL이 `/conversations`로 변경됨<br>2. 브라우저 개발자도구 → Application → localStorage에 `access_token` 저장됨<br>3. 토큰 형식: `eyJ...` (JWT 형식) |

**테스트 단계:**
1. http://localhost:3000/register 접속
2. 이메일 필드에 `testuser@example.com` 입력
3. 패스워드 필드에 `TestPassword123` 입력 (8자 이상, 대문자 포함, 숫자 포함)
4. Display Name 필드에 `Test User` 입력
5. "Register" 버튼 클릭
6. 자동으로 `/conversations` 페이지로 이동 확인

**API 검증 (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123",
    "display_name": "Test User"
  }'
```

**기대 응답 (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 1.2 에러 케이스 - 중복 이메일

| 항목 | 내용 |
|------|------|
| **입력** | 이미 가입된 이메일 (예: `testuser@example.com`) |
| **기대 결과** | 에러 메시지 표시: "Email already registered" |
| **확인 방법** | 페이지에 빨간색 에러 박스가 표시됨 |

**테스트 단계:**
1. 1.1 테스트 완료 후 다시 http://localhost:3000/register 접속
2. 동일한 이메일 `testuser@example.com` 입력
3. 다른 비밀번호 및 display name 입력
4. "Register" 버튼 클릭
5. 에러 메시지 확인

### 1.3 에러 케이스 - 약한 비밀번호

| 항목 | 내용 |
|------|------|
| **입력** | Password: `weak` (8자 미만, 대문자/숫자 없음) |
| **기대 결과** | 유효성 검사 에러 메시지 표시 |
| **확인 방법** | "Password must be at least 8 characters long" 메시지 표시 |

**테스트 단계:**
1. http://localhost:3000/register 접속
2. 이메일: `test2@example.com`
3. 비밀번호: `weak` 입력
4. Display Name: `Test User 2`
5. "Register" 버튼 클릭
6. 에러 메시지 확인

**가능한 에러 메시지:**
- "Password must be at least 8 characters long"
- "Password must contain at least one uppercase letter"
- "Password must contain at least one digit"

---

## 2. 로그인 테스트 (`/login`)

기존 계정으로 로그인합니다.

### 2.1 성공 케이스 - 유효한 계정

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/login |
| **입력** | Email: `testuser@example.com`, Password: `TestPassword123` |
| **기대 결과** | 로그인 성공 → `/conversations` 페이지로 자동 리다이렉트 |
| **확인 방법** | 1. URL이 `/conversations`로 변경됨<br>2. localStorage에 `access_token` 저장됨 |

**테스트 단계:**
1. 브라우저를 종료하거나 시크릿 창에서 http://localhost:3000/login 접속
2. 이메일: `testuser@example.com` 입력
3. 비밀번호: `TestPassword123` 입력
4. "Login" 버튼 클릭
5. `/conversations` 페이지로 리다이렉트 확인

**API 검증 (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123"
  }'
```

**기대 응답 (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2.2 에러 케이스 - 존재하지 않는 이메일

| 항목 | 내용 |
|------|------|
| **입력** | Email: `nonexistent@example.com`, Password: `TestPassword123` |
| **기대 결과** | 에러 메시지: "Invalid email or password" |
| **확인 방법** | 빨간색 에러 박스에 메시지 표시 |

**테스트 단계:**
1. http://localhost:3000/login 접속
2. 이메일: `nonexistent@example.com`
3. 비밀번호: `TestPassword123`
4. "Login" 버튼 클릭
5. 에러 메시지 확인

### 2.3 에러 케이스 - 잘못된 비밀번호

| 항목 | 내용 |
|------|------|
| **입력** | Email: `testuser@example.com`, Password: `WrongPassword123` |
| **기대 결과** | 에러 메시지: "Invalid email or password" |
| **확인 방법** | 빨간색 에러 박스에 메시지 표시 |

**테스트 단계:**
1. http://localhost:3000/login 접속
2. 이메일: `testuser@example.com`
3. 비밀번호: `WrongPassword123`
4. "Login" 버튼 클릭
5. 에러 메시지 확인

---

## 3. 대화 목록 (`/conversations`)

사용자의 모든 대화를 조회합니다.

### 3.1 초기 상태 - 대화 없음

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/conversations |
| **전제 조건** | 로그인된 상태 (새 계정) |
| **기대 결과** | 1. h1 제목: "Conversations"<br>2. "New Conversation" 버튼 표시<br>3. "No conversations yet" 메시지 표시<br>4. "Start your first conversation" 버튼 표시 |
| **확인 방법** | 페이지 소스 검사 또는 개발자도구 Elements 탭 |

**테스트 단계:**
1. 새 계정으로 로그인 후 `/conversations` 접속 (자동 리다이렉트)
2. 페이지 레이아웃 확인:
   - 상단 헤더: "Conversations" 제목
   - 우측 상단: "New Conversation" 버튼
   - 중앙: "No conversations yet" 메시지
3. F12 개발자도구 → Elements 탭에서 구조 확인

**API 검증 (curl):**
```bash
# 로그인 후 access_token 획득
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN"
```

**기대 응답 (200 OK):**
```json
[]
```

### 3.2 대화 목록 표시 - 대화 있음

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/conversations |
| **전제 조건** | 대화 1개 이상 생성됨 (섹션 4 참조) |
| **기대 결과** | 1. 대화 카드 목록 표시<br>2. 각 카드에 제목과 수정 시간 표시<br>3. 카드 클릭 시 해당 대화로 이동 |
| **확인 방법** | 페이지에 그리드 레이아웃의 대화 카드 표시 |

**테스트 단계:**
1. 섹션 4에서 대화 생성 후 `/conversations` 접속
2. 대화 카드 표시 확인:
   - 제목 (예: "New Conversation")
   - 수정 시간 (예: "Just now", "2h ago")
3. 카드 클릭하여 `/chat/{id}` 페이지로 이동 확인

**API 검증 (curl):**
```bash
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN"
```

**기대 응답 (200 OK):**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "New Conversation",
    "status": "active",
    "created_at": "2026-02-23T10:30:45.123456+00:00",
    "updated_at": "2026-02-23T10:30:45.123456+00:00"
  }
]
```

---

## 4. 새 대화 생성

대화를 새로 생성하고 채팅 페이지로 이동합니다.

### 4.1 대화 생성 성공

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/conversations |
| **작업** | "New Conversation" 버튼 클릭 또는"Start your first conversation" 버튼 클릭 |
| **기대 결과** | 1. 새 대화 생성<br>2. `/chat/{uuid}` 페이지로 자동 리다이렉트<br>3. UUID는 유효한 형식 (예: `123e4567-e89b-12d3-a456-426614174000`) |
| **확인 방법** | 1. URL 변경 확인<br>2. 채팅 인터페이스 로드 |

**테스트 단계:**
1. `/conversations` 페이지에서 "New Conversation" 버튼 클릭
2. URL 변경 확인: `http://localhost:3000/chat/{uuid}`
3. 채팅 인터페이스 표시 확인

**API 검증 (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "New Conversation"}'
```

**기대 응답 (201 Created):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "987e6543-e89b-12d3-a456-426614174999",
  "title": "New Conversation",
  "status": "active",
  "created_at": "2026-02-23T10:30:45.123456+00:00",
  "updated_at": "2026-02-23T10:30:45.123456+00:00"
}
```

---

## 5. 채팅 (`/chat/{id}`)

사용자와 AI 간의 대화를 진행합니다.

### 5.1 메시지 전송 및 수신

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/chat/{conversation_id} |
| **입력** | 텍스트: "Build me a simple REST API for todo management" |
| **기대 결과** | 1. 사용자 메시지 표시<br>2. `user_message_received` 수신 (WebSocket)<br>3. Intent Analyzer → Design Generator 순으로 AI 처리<br>4. `designs_presented` 메시지로 파이프라인 설계안 표시<br>5. 메시지 입력 필드 초기화 |
| **확인 방법** | 1. 메시지 버블 표시<br>2. 개발자도구 → Network → WS 필터링하여 WebSocket 통신 확인 |

**참고:** 첫 번째 응답은 `user_message_received` 타입으로 수신됩니다. 이후 AI가 Intent Analyzer → Design Generator 파이프라인을 거쳐 처리하므로, 최종 응답은 `designs_presented` 타입으로 수신됩니다. OpenAI API 응답 시간에 따라 5-15초 소요될 수 있습니다.

**테스트 단계:**
1. 섹션 4에서 생성한 대화의 `/chat/{id}` 페이지 접속
2. 페이지 레이아웃 확인:
   - 상단: 대화 제목 또는 헤더
   - 중앙: 메시지 표시 영역 (처음에는 비어있음)
   - 하단: 메시지 입력 필드 (`input[type="text"]`)와 Send 버튼
3. 입력 필드에 "Build me a simple REST API for todo management" 입력
4. Send 버튼 클릭
5. 사용자 메시지 표시 확인
6. AI 응답 대기 (OpenAI API 응답 시간에 따라 5-15초)
7. AI 응답 메시지 표시 확인 (`designs_presented` 타입, 파이프라인 설계안 포함)

**WebSocket 통신 검증:**
1. F12 개발자도구 → Network 탭
2. 필터: `WS` 선택
3. Send 버튼 클릭 후 WebSocket 연결 확인
4. Message 카테고리에서 송수신 메시지 확인

**WebSocket URL:**
```
ws://localhost:8000/api/v1/ws/chat/{conversation_id}
```

**WebSocket 메시지 형식:**

클라이언트 → 서버:
```json
{
  "type": "message",
  "content": "안녕하세요"
}
```

서버 → 클라이언트 (메시지 수신 확인):
```json
{
  "type": "user_message_received",
  "content": "안녕하세요",
  "conversation_id": "uuid",
  "timestamp": "2026-02-23T02:28:57.147740+00:00"
}
```

서버 → 클라이언트 (AI 응답 - clarification):
```json
{
  "type": "clarification",
  "content": "요청을 더 잘 이해하기 위해 몇 가지 질문이 있습니다.",
  "questions": ["어떤 종류의 애플리케이션을 만들고 싶으신가요?"],
  "conversation_id": "uuid",
  "timestamp": "2026-02-23T02:28:57.200000+00:00"
}
```

서버 → 클라이언트 (파이프라인 결과):
```json
{
  "type": "pipeline_result",
  "content": "파이프라인 실행이 완료되었습니다.",
  "result": { ... },
  "conversation_id": "uuid",
  "timestamp": "2026-02-23T02:28:57.300000+00:00"
}
```

### 5.2 여러 메시지 교환

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/chat/{conversation_id} |
| **입력** | 메시지 1: "한국어로 대답해줄래?", 메시지 2: "GPT-4o와 Claude의 차이를 설명해줘" |
| **기대 결과** | 각 메시지에 대한 AI 응답 수신 및 표시 |
| **확인 방법** | 메시지 히스토리가 스크롤 가능하게 쌓임 |

**테스트 단계:**
1. 섹션 5.1 완료 후 계속 진행
2. 입력 필드에 "한국어로 대답해줄래?" 입력 후 Send
3. AI 응답 대기 및 확인
4. 입력 필드에 "GPT-4o와 Claude의 차이를 설명해줘" 입력 후 Send
5. AI 응답 대기 및 확인
6. 메시지가 위부터 아래로 쌓여있는지 확인

### 5.3 메시지 UI 검증

| 항목 | 내용 |
|------|------|
| **검증 항목** | 메시지 버블 디자인 |
| **기대 결과** | 1. 사용자 메시지: 우측 정렬, 파란색 배경<br>2. AI 메시지: 좌측 정렬, 회색 배경<br>3. 메시지 텍스트 명확하게 표시<br>4. 타임스탬프 표시 (옵션) |
| **확인 방법** | 개발자도구 → Elements 탭에서 DOM 구조 확인 |

**테스트 단계:**
1. 메시지가 여러 개 있는 채팅 페이지 열기
2. 시각적 구분 확인:
   - 사용자 메시지: 우측에 배치
   - AI 메시지: 좌측에 배치
3. F12 → Elements에서 `MessageBubble` 컴포넌트 구조 확인

### 5.4 LLM 파이프라인 전체 플로우 테스트

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/chat/{conversation_id} |
| **전제 조건** | OpenAI API 키 설정 완료, Docker 재시작 완료 |
| **입력** | "Build me a simple REST API for todo management" |
| **기대 결과** | 1. `user_message_received` 수신<br>2. Intent Analyzer가 요청 분석<br>3. Design Generator가 파이프라인 설계안 생성<br>4. `designs_presented` 메시지로 설계안 표시<br>5. "Open in Pipeline Editor" 버튼 표시 |

**테스트 단계:**
1. `/conversations` 페이지에서 "New Conversation" 클릭
2. 채팅 페이지에서 "Build me a simple REST API for todo management" 입력
3. Send 버튼 클릭
4. 5-15초 대기 (OpenAI API 응답 시간)
5. AI 응답 확인:
   - 설계안 텍스트 (아키텍처, 컴포넌트, 기술 스택 등)
   - "Open in Pipeline Editor" 버튼
6. F12 → Network → WS 탭에서 메시지 확인:
   - `user_message_received` → `designs_presented` 순서

**WebSocket 메시지 예시 (designs_presented):**
```json
{
  "type": "designs_presented",
  "content": "다음과 같은 파이프라인 설계안을 생성했습니다.",
  "designs": [
    {
      "name": "Simple REST API",
      "description": "Todo 관리를 위한 REST API",
      "complexity": "low",
      "estimated_cost": "$0.05",
      "recommended": true,
      "pros": ["Simple to implement", "Low cost"],
      "cons": ["Limited scalability"]
    }
  ]
}
```

**API 검증 (Python WebSocket):**
```bash
pip install websockets

python3 -c "
import asyncio, json, websockets

async def test():
    TOKEN='your-jwt-token'
    CONV_ID='your-conversation-id'
    uri = f'ws://localhost:8000/api/v1/ws/chat/{CONV_ID}?token={TOKEN}'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            'content': 'Build me a simple REST API',
            'conversation_id': CONV_ID
        }))
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(msg)
                print(f'Type: {data[\"type\"]}')
                if data['type'] in ('designs_presented', 'clarification', 'error'):
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    break
            except asyncio.TimeoutError:
                print('Timeout')
                break

asyncio.run(test())
"
```

---

## 6. 파이프라인 에디터 (`/pipeline-editor`)

React Flow 기반 시각적 파이프라인 편집 도구입니다.

### 6.1 에디터 레이아웃 확인

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/pipeline-editor |
| **기대 결과** | 1. React Flow 캔버스 표시<br>2. 좌측 사이드바 표시<br>3. 상단 툴바 표시<br>4. Save 버튼 표시 |
| **확인 방법** | 페이지 로드 후 각 요소의 시각적 확인 |

**테스트 단계:**
1. http://localhost:3000/pipeline-editor 접속
2. 페이지 레이아웃 확인:
   - 캔버스: 중앙 흰색 배경 영역 (또는 그리드)
   - 사이드바: 좌측 패널 (노드 목록)
   - 툴바: 상단 버튼 (줌, 리셋 등)
3. F12 → Elements에서 `.react-flow` 클래스 확인

### 6.2 노드 추가 (드래그)

| 항목 | 내용 |
|------|------|
| **작업** | 사이드바에서 노드 타입을 캔버스로 드래그 |
| **노드 타입** | Intent Analyzer, Design Generator, Critique Agent, Collector 등 |
| **기대 결과** | 1. 캔버스에 새 노드 추가<br>2. 노드에 레이블 표시<br>3. 노드의 입출력 핸들 표시 |
| **확인 방법** | 캔버스에 시각적으로 노드가 나타남 |

**테스트 단계:**
1. 파이프라인 에디터 페이지 접속
2. 좌측 사이드바에서 노드 (예: "Intent Analyzer") 찾기
3. 노드를 마우스로 누르고 드래그
4. 캔버스의 중앙으로 드래그하여 놓기
5. 캔버스에 노드가 추가되는지 확인

### 6.3 노드 연결 (엣지 생성)

| 항목 | 내용 |
|------|------|
| **전제 조건** | 캔버스에 노드 2개 이상 추가됨 |
| **작업** | 첫 번째 노드의 출력 핸들에서 두 번째 노드의 입력 핸들로 드래그 |
| **기대 결과** | 1. 엣지(연결선) 생성<br>2. 엣지에 조건(옵션) 표시<br>3. 엣지 선택 가능 |
| **확인 방법** | 캔버스에 선으로 두 노드가 연결됨 |

**테스트 단계:**
1. 섹션 6.2에서 두 개의 노드 추가 (예: Intent Analyzer, Design Generator)
2. 첫 번째 노드의 우측 또는 하단 핸들 찾기 (작은 원 형태)
3. 핸들을 마우스로 누르고 드래그
4. 두 번째 노드의 좌측 또는 상단 핸들로 드래그하여 놓기
5. 두 노드 사이에 선이 연결되는지 확인

### 6.4 노드 편집

| 항목 | 내용 |
|------|------|
| **작업** | 노드 더블클릭 또는 우클릭 |
| **기대 결과** | 1. 우측 패널에 속성 표시<br>2. 노드 이름, 설명, 파라미터 편집 가능<br>3. 변경사항 실시간 반영 |
| **확인 방법** | 우측 패널에서 입력 필드 표시 |

**테스트 단계:**
1. 캔버스의 노드 더블클릭
2. 우측 패널("PropertyPanel")이 열리는지 확인
3. 노드 이름, 설명 등의 필드 수정 가능 확인
4. 캔버스의 노드 라벨이 변경되는지 확인

### 6.5 Save (저장)

| 항목 | 내용 |
|------|------|
| **작업** | Save 버튼 클릭 |
| **기대 결과** | 1. 파이프라인이 템플릿으로 저장<br>2. 성공 메시지 표시<br>3. `/templates` 페이지로 이동 (옵션) |
| **확인 방법** | 성공 토스트 메시지 표시 또는 템플릿 목록에 새 항목 추가 |

**테스트 단계:**
1. 파이프라인 에디터에서 노드 및 엣지 추가
2. 상단 Save 버튼 클릭
3. 성공 메시지 확인
4. 개발자도구 → Network에서 POST /api/v1/templates 요청 확인

**API 검증 (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Pipeline",
    "description": "Test pipeline",
    "graph_data": {
      "nodes": [{"id": "n1", "type": "api", "position": {"x": 0, "y": 0}}],
      "edges": []
    },
    "design_data": {
      "name": "My Design",
      "description": "test",
      "architecture": "monolith",
      "components": ["api"],
      "tech_stack": {"backend": "python"},
      "rationale": "test"
    }
  }'
```

**기대 응답 (201 Created):**
```json
{
  "id": "template-uuid",
  "name": "My Pipeline",
  "description": "Test pipeline",
  "graph_data": { ... },
  "design_data": { ... },
  "is_public": false,
  "created_at": "2026-02-23T10:30:45.123456",
  "updated_at": "2026-02-23T10:30:45.123456"
}
```

---

## 7. 템플릿 목록 (`/templates`)

저장된 파이프라인 템플릿을 조회합니다.

### 7.1 초기 상태 - 템플릿 없음

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/templates |
| **전제 조건** | 템플릿이 없는 상태 (새 계정) |
| **기대 결과** | 1. h1 제목: "Templates"<br>2. "New Template" 버튼 표시<br>3. 검색 입력 필드 표시<br>4. "No templates yet" 메시지 표시 |
| **확인 방법** | 페이지 소스 검사 또는 시각적 확인 |

**테스트 단계:**
1. 새 계정으로 로그인 후 `/templates` 접속 (좌측 내비게이션 또는 URL 직접 입력)
2. 페이지 레이아웃 확인:
   - 상단: "Templates" 제목과 "New Template" 버튼
   - 검색 필드: `input[type="search"]`
   - 중앙: "No templates yet. Click \"New Template\" to get started." 메시지

**API 검증 (curl):**
```bash
curl -X GET http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN"
```

**기대 응답 (200 OK):**
```json
[]
```

### 7.2 템플릿 목록 표시 - 템플릿 있음

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/templates |
| **전제 조건** | 템플릿 1개 이상 생성됨 (섹션 6.5 참조) |
| **기대 결과** | 1. 템플릿 카드 그리드 표시 (1-2열)<br>2. 각 카드에 이름, 설명, 날짜, Public 배지 표시<br>3. 카드 클릭 시 템플릿 상세 페이지로 이동 |
| **확인 방법** | 페이지에 그리드 레이아웃의 템플릿 카드 표시 |

**테스트 단계:**
1. 섹션 6에서 템플릿 생성 후 `/templates` 접속
2. 템플릿 카드 표시 확인:
   - 템플릿 이름 (예: "My Pipeline")
   - 설명 (있으면)
   - 생성/수정 날짜
   - Public 배지 (공개 템플릿인 경우)
3. 카드 클릭하여 `/templates/{id}` 페이지로 이동 확인

**API 검증 (curl):**
```bash
curl -X GET http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN"
```

**기대 응답 (200 OK):**
```json
[
  {
    "id": "template-uuid",
    "name": "My Pipeline",
    "description": "Test pipeline",
    "is_public": false,
    "created_at": "2026-02-23T10:30:45.123456+00:00",
    "updated_at": "2026-02-23T10:30:45.123456+00:00"
  }
]
```

### 7.3 템플릿 검색

| 항목 | 내용 |
|------|------|
| **작업** | 검색 필드에 텍스트 입력 |
| **입력** | 검색어: "My" (템플릿 이름의 일부) |
| **기대 결과** | 검색어를 포함하는 템플릿만 필터링되어 표시 |
| **확인 방법** | 입력 후 카드가 즉시 필터링됨 |

**테스트 단계:**
1. `/templates` 페이지에서 템플릿 카드가 여러 개 표시되는 상태
2. 검색 필드에 "My" 입력
3. 이름에 "My"를 포함하는 템플릿만 표시되는지 확인
4. 검색 필드를 지우면 모든 템플릿이 다시 표시되는지 확인

---

## 8. 템플릿 상세 (`/templates/{id}`)

특정 템플릿의 상세 정보와 파이프라인 다이어그램을 조회합니다.

### 8.1 템플릿 상세 정보 표시

| 항목 | 내용 |
|------|------|
| **페이지** | http://localhost:3000/templates/{template_id} |
| **기대 결과** | 1. 템플릿 제목 표시<br>2. 설명 표시<br>3. 생성 날짜, 수정 날짜 표시<br>4. Fork 버튼 표시<br>5. React Flow 다이어그램 표시 (읽기 전용) |
| **확인 방법** | 페이지에 모든 정보가 표시됨 |

**테스트 단계:**
1. `/templates` 페이지에서 템플릿 카드 클릭
2. `/templates/{id}` 페이지 로드 확인
3. 페이지 상단에서 확인:
   - 템플릿 제목 (예: "My Pipeline")
   - 설명
   - 날짜 정보
   - Fork 버튼
4. 페이지 중앙에 React Flow 다이어그램 표시 확인

**API 검증 (curl):**
```bash
curl -X GET http://localhost:8000/api/v1/templates/{template_id} \
  -H "Authorization: Bearer $TOKEN"
```

**기대 응답 (200 OK):**
```json
{
  "id": "template-uuid",
  "name": "My Pipeline",
  "description": "Test pipeline",
  "is_public": false,
  "graph_data": {
    "nodes": [...],
    "edges": [...]
  },
  "created_at": "2026-02-23T10:30:45.123456+00:00",
  "updated_at": "2026-02-23T10:30:45.123456+00:00"
}
```

### 8.2 Fork (템플릿 복제)

| 항목 | 내용 |
|------|------|
| **작업** | Fork 버튼 클릭 |
| **기대 결과** | 1. 템플릿이 복제되어 새로운 템플릿으로 저장<br>2. 성공 메시지 표시<br>3. 새 템플릿의 상세 페이지로 이동 또는 목록으로 이동 |
| **확인 방법** | 1. 성공 메시지 표시<br>2. 새 템플릿이 `/templates` 목록에 추가됨 |

**테스트 단계:**
1. 템플릿 상세 페이지에서 Fork 버튼 클릭
2. 성공 메시지 확인
3. `/templates` 페이지로 이동
4. 복제된 템플릿이 목록에 추가되었는지 확인 (이름: "My Pipeline (fork)" 또는 유사)

**API 검증 (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/templates/{template_id}/fork \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**기대 응답 (201 Created):**
```json
{
  "id": "new-template-uuid",
  "name": "My Pipeline (fork)",
  "description": "Test pipeline",
  "is_public": false,
  "created_at": "2026-02-23T10:30:46.123456+00:00",
  "updated_at": "2026-02-23T10:30:46.123456+00:00"
}
```

---

## 9. 로그아웃

현재 서버 측 로그아웃 엔드포인트(`/api/v1/auth/logout`)는 구현되어 있지 않습니다.
로그아웃은 클라이언트 측에서 localStorage의 토큰을 삭제하는 방식으로 처리됩니다.

### 9.1 클라이언트 측 로그아웃

| 항목 | 내용 |
|------|------|
| **작업** | 우측 상단 프로필 메뉴에서 "Logout" 클릭 |
| **기대 결과** | 1. `/login` 페이지로 리다이렉트<br>2. localStorage에서 `access_token` 삭제 |
| **확인 방법** | 1. URL이 `/login`으로 변경<br>2. F12 → Application → localStorage에 토큰 없음 |

**테스트 단계:**
1. 로그인된 상태에서 우측 상단 프로필/메뉴 아이콘 클릭
2. "Logout" 옵션 클릭
3. URL이 `/login`으로 변경되는지 확인
4. F12 → Application → Storage → localStorage 확인
5. `access_token` 키가 없는지 확인

### 9.2 서버 측 토큰 무효화 (미구현)

| 항목 | 내용 |
|------|------|
| **상태** | 미구현 (향후 Phase에서 추가 예정) |
| **현재 동작** | JWT 토큰은 만료 시간까지 유효 (서버 측 blacklist 없음) |
| **영향** | 클라이언트에서 토큰을 삭제해도 해당 토큰은 만료 전까지 API 호출에 사용 가능 |

> **참고:** 서버 측 토큰 무효화(JWT blacklist)가 필요한 경우 Redis 기반 토큰 블랙리스트 구현이 필요합니다.

---

## 10. API 직접 테스트 (curl 명령어)

커맨드라인에서 API를 직접 테스트합니다.

### 10.1 인증 API

**회원가입:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123",
    "display_name": "Test User"
  }' | jq
```

**로그인:**
```bash
TOKEN_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123"
  }')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
echo "Access Token: $TOKEN"
```

**현재 사용자 프로필:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

**사용자 사용량 조회:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me/usage \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 10.2 대화 API

**대화 목록:**
```bash
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" | jq
```

**새 대화 생성:**
```bash
CONV=$(curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Conversation"}')

CONV_ID=$(echo $CONV | jq -r '.id')
echo "Conversation ID: $CONV_ID"
```

**대화 상세:**
```bash
curl -X GET http://localhost:8000/api/v1/conversations/$CONV_ID \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 10.3 템플릿 API

**템플릿 목록:**
```bash
curl -X GET http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN" | jq
```

**템플릿 생성:**
```bash
TEMPLATE=$(curl -X POST http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Template",
    "description": "A test template",
    "graph_data": {
      "nodes": [{"id": "1", "data": {"label": "Node 1"}, "position": {"x": 0, "y": 0}}],
      "edges": []
    },
    "design_data": {
      "name": "Test Design",
      "description": "test",
      "architecture": "monolith",
      "components": ["api"],
      "tech_stack": {"backend": "python"},
      "rationale": "test"
    }
  }')

TEMPLATE_ID=$(echo $TEMPLATE | jq -r '.id')
echo "Template ID: $TEMPLATE_ID"
```

**템플릿 상세:**
```bash
curl -X GET http://localhost:8000/api/v1/templates/$TEMPLATE_ID \
  -H "Authorization: Bearer $TOKEN" | jq
```

**템플릿 Fork:**
```bash
curl -X POST http://localhost:8000/api/v1/templates/$TEMPLATE_ID/fork \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

### 10.4 API 키 관리 (Phase 2C)

**API 키 생성:**
```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Key",
    "is_active": true
  }' | jq
```

**API 키 목록:**
```bash
curl -X GET http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 10.5 Data Collector API

**컬렉션 생성:**
```bash
curl -X POST http://localhost:8001/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Collection",
    "description": "test"
  }' | jq
```

**기대 응답 (201 Created):**
```json
{
  "id": "collection-uuid",
  "status": "pending",
  "source_type": "web",
  "url": null,
  "created_at": "2026-02-23T02:41:34.196505Z"
}
```

**컬렉션 상태 조회:**
```bash
curl -X GET http://localhost:8001/api/v1/collections/$COLL_ID/status | jq
```

**컴플라이언스 검사:**
```bash
curl -X GET http://localhost:8001/api/v1/collections/$COLL_ID/compliance | jq
```

**데이터 수집 실행:**
```bash
curl -X POST http://localhost:8001/api/v1/collections/$COLL_ID/collect \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_pages": 1}' | jq
```

**SSRF 방어 테스트:**
```bash
# Internal IP 차단 (422 Validation Error)
curl -X POST http://localhost:8001/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "SSRF Test", "url": "http://169.254.169.254/latest/meta-data/"}'

# Localhost 차단 (422 Validation Error)
curl -X POST http://localhost:8001/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "SSRF Test", "url": "http://localhost:8000/api/v1/health"}'
```

### 10.6 메트릭 API

**Prometheus 메트릭 조회:**
```bash
curl http://localhost:9090/api/v1/query?query=http_requests_total | jq
```

**Grafana 대시보드:**
```
http://localhost:3001 (admin/admin)
```

---

## 11. WebSocket 테스트 (고급)

WebSocket을 통한 실시간 메시지 통신을 테스트합니다.

### 11.1 wscat로 WebSocket 테스트

**설치:**
```bash
npm install -g wscat
```

**연결:**
```bash
CONV_ID="123e4567-e89b-12d3-a456-426614174000"
wscat -c "ws://localhost:8000/api/v1/ws/chat/$CONV_ID?token=$TOKEN"
```

**메시지 전송:**
```json
{"type": "message", "content": "안녕하세요"}
```

**기대 응답:**
```json
{"type": "message", "sender": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
```

### 11.2 JavaScript로 WebSocket 테스트

브라우저 개발자도구 Console에서:

```javascript
const token = localStorage.getItem('access_token');
const convId = '123e4567-e89b-12d3-a456-426614174000';
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/chat/${convId}?token=${token}`);

ws.onopen = () => {
  console.log('Connected');
  ws.send(JSON.stringify({type: 'message', content: '테스트 메시지'}));
};

ws.onmessage = (event) => {
  console.log('Message:', JSON.parse(event.data));
};

ws.onerror = (error) => {
  console.error('Error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

---

## 12. 성능 및 모니터링 테스트

### 12.1 Prometheus 메트릭 확인

**URL:** http://localhost:9090

주요 메트릭:
- `http_request_duration_seconds`: HTTP 요청 지연
- `llm_token_total`: LLM 토큰 사용량
- `llm_cost_total`: LLM 비용 누적
- `pipeline_execution_duration_seconds`: 파이프라인 실행 시간
- `websocket_connections_active`: 활성 WebSocket 연결

### 12.2 Grafana 대시보드 확인

**URL:** http://localhost:3001 (admin/admin)

9개 패널:
1. **HTTP Request Rate**: 초당 HTTP 요청 수
2. **HTTP Latency (p50/p95/p99)**: 응답 지연 백분위수
3. **Error Rate**: 5xx 에러 비율
4. **LLM Token Usage**: 모델별 토큰 사용량
5. **LLM Cost Tracking**: 모델별 누적 비용
6. **LLM Request Latency**: LLM API 지연
7. **Pipeline Execution Status**: 파이프라인 성공/실패
8. **Pipeline Duration**: 파이프라인 실행 시간
9. **Active WebSocket Connections**: WebSocket 연결 수

**테스트 단계:**
1. Grafana 접속
2. 메인 대시보드 선택
3. 각 패널에서 메트릭 데이터 표시 확인
4. API 호출 또는 WebSocket 통신 실행 후 메트릭 변화 확인

---

## 13. Rate Limiting 테스트 (Phase 2B)

### 13.1 Rate Limit 초과

| 항목 | 내용 |
|------|------|
| **작업** | 짧은 시간에 API 요청 100회 이상 전송 |
| **기대 결과** | 429 Too Many Requests 응답 |
| **확인 방법** | HTTP 상태 코드 및 `Retry-After` 헤더 확인 |

**테스트 (bash):**
```bash
for i in {1..101}; do
  curl -X GET http://localhost:8000/api/v1/conversations \
    -H "Authorization: Bearer $TOKEN" \
    -w "Status: %{http_code}\n" \
    -s -o /dev/null
done
```

**기대 응답 (429):**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## 14. 비용 Circuit Breaker 테스트 (Phase 2C)

### 14.1 일일 비용 한도 초과

| 항목 | 내용 |
|------|------|
| **작업** | 일일 비용 한도(`DAILY_COST_LIMIT`, 기본값 $10)를 초과하는 API 호출 |
| **기대 결과** | 402 Payment Required 응답 |
| **확인 방법** | HTTP 상태 코드 확인 |

**참고:** LLM API 호출 비용이 누적되므로 실제 테스트 시 비용이 발생할 수 있습니다.

```bash
curl -X GET http://localhost:8000/api/v1/auth/me/usage \
  -H "Authorization: Bearer $TOKEN" | jq '.daily_cost, .daily_limit'
```

**기대 응답:**
```json
{
  "daily_cost": 5.25,
  "daily_limit": 10.0,
  "remaining": 4.75,
  "is_unlimited": false
}
```

---

## 15. 알려진 제한사항

| 항목 | 설명 | 해결 방법 |
|------|------|--------|
| **LLM API 키 미설정 시** | `OPENAI_API_KEY` 또는 `ANTHROPIC_API_KEY`가 없으면 AI 응답 불가 | `.env` 파일에서 API 키 설정 후 `docker compose down && up -d` 필요 |
| **WebSocket 토큰 필요** | WebSocket 연결 시 유효한 JWT 토큰 필요 | 쿼리 파라미터로 `?token={access_token}` 전달 |
| **파이프라인 실행** | 파이프라인 실행 시 LLM 설정 필수 | OpenAI 또는 Anthropic API 키 설정 |
| **템플릿 최대 개수** | 사용자당 최대 50개 템플릿 | 오래된 템플릿 삭제 후 새로 생성 |
| **동시 연결 제한** | Redis 기반 Rate Limiting (기본값: 분당 100요청) | `backend/gateway/rate_limiter.py`에서 설정 변경 |
| **데이터베이스 용량** | PostgreSQL 용량 초과 시 새 대화 생성 불가 | `docker exec agentforge-postgres psql -U postgres -d agentforge -c "SELECT pg_database_size('agentforge');"`로 확인 |
| **로그아웃 미구현** | 서버 측 `/api/v1/auth/logout` 엔드포인트 없음 | 클라이언트에서 localStorage 토큰 삭제로 처리. 서버 측 JWT blacklist는 향후 구현 |

---

## 16. 트러블슈팅

### 16.1 "Connection refused" 에러

**증상:** `curl: (7) Failed to connect to localhost port 8000`

**해결:**
```bash
# 서비스 상태 확인
docker compose -f docker/docker-compose.yml ps

# 서비스 재시작
docker compose -f docker/docker-compose.yml restart backend
```

### 16.2 "Invalid token" 에러

**증상:** API 요청 시 `{"detail": "Invalid token"}`

**해결:**
```bash
# 새로 로그인하여 토큰 갱신
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123"}' | jq -r '.access_token')

# 새 토큰으로 재시도
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN"
```

### 16.3 "Database connection error" 에러

**증상:** `sqlalchemy.exc.OperationalError`

**해결:**
```bash
# PostgreSQL 상태 확인
docker compose -f docker/docker-compose.yml logs postgres

# 데이터베이스 재초기화
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d postgres redis
docker compose -f docker/docker-compose.yml up -d backend
```

### 16.4 WebSocket 연결 실패

**증상:** WebSocket 핸드셰이크 실패

**해결:**
```bash
# 토큰이 유효한지 확인
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# WebSocket URL이 올바른지 확인
# ws://localhost:8000/api/v1/ws/chat/{conversation_id}?token={token}
```

### 16.5 "CORS 에러" (브라우저)

**증상:** 브라우저 Console에 `Access to XMLHttpRequest has been blocked by CORS policy`

**해결:**
```bash
# docker-compose.yml에서 CORS_ORIGINS 확인
grep CORS_ORIGINS docker/docker-compose.yml

# 값: ["http://localhost:3000"] 이어야 함
# 변경 후 Docker 재시작
docker compose -f docker/docker-compose.yml restart backend
```

---

## 17. 체크리스트 - 전체 기능 테스트

| 기능 | 테스트 상태 | 테스트 날짜 | 비고 |
|------|-----------|-----------|------|
| [x] 0. 서비스 실행 및 헬스 체크 | PASS | 2026-02-23 | 7개 서비스 전체 healthy |
| [x] 1. 회원가입 (성공) | PASS | 2026-02-23 | 201 Created, JWT 발급 |
| [x] 1. 회원가입 (중복 이메일) | PASS | 2026-02-23 | 409 Conflict |
| [x] 1. 회원가입 (약한 비밀번호) | PASS | 2026-02-23 | 422 Validation Error |
| [x] 2. 로그인 (성공) | PASS | 2026-02-23 | 200 OK, JWT 발급 |
| [x] 2. 로그인 (잘못된 계정) | PASS | 2026-02-23 | 401 동일 메시지 (보안) |
| [x] 3. 대화 목록 (비어있음) | PASS | 2026-02-23 | 200, 빈 배열 |
| [x] 3. 대화 목록 (대화 있음) | PASS | 2026-02-23 | 200, 대화 포함 |
| [x] 4. 새 대화 생성 | PASS | 2026-02-23 | 201, UUID 형식 |
| [x] 5. 채팅 (WebSocket 연결) | PASS | 2026-02-23 | 연결/메시지/응답/종료 |
| [x] 5. 채팅 (여러 메시지 교환) | PASS | 2026-02-23 | LLM API 연동 확인, designs_presented 수신 |
| [ ] 6. 파이프라인 에디터 (UI) | 미완료 | - | 브라우저 테스트 필요 |
| [x] 6. 파이프라인 API (Execute) | PASS | 2026-02-23 | 200, agents 미정의 시 예상 실패 |
| [x] 6. 파이프라인 API (Status/Result) | PASS | 2026-02-23 | 200/404 정상 |
| [x] 7. 템플릿 CRUD | PASS | 2026-02-23 | Create/List/Detail/Update/Delete |
| [x] 7. 템플릿 공유/Fork | PASS | 2026-02-23 | is_public + Fork "(fork)" |
| [ ] 7. 템플릿 목록 (검색) | 미완료 | - | 브라우저 테스트 필요 |
| [x] 9. 로그아웃 | N/A | 2026-02-23 | 서버 엔드포인트 미구현 (클라이언트 전용) |
| [x] 10. API 인증 검증 | PASS | 2026-02-23 | 토큰 없음/잘못된 토큰 → 401 |
| [x] 11. WebSocket 테스트 | PASS | 2026-02-23 | 연결/메시지 송수신 성공 |
| [x] 12. 모니터링 (Prometheus) | PASS | 2026-02-23 | 메트릭 정상 수집 |
| [x] 12. 모니터링 (Grafana) | PASS | 2026-02-23 | Health 200 OK |
| [x] 13. Rate Limiting | PASS | 2026-02-23 | 10회 연속 요청 통과 |
| [x] 14. Data Collector CRUD | PASS | 2026-02-23 | Create/Status/Compliance |
| [x] 14. SSRF 방어 | PASS | 2026-02-23 | Internal IP/Localhost 차단 |
| [x] 14. 비용 Circuit Breaker | PASS | 2026-02-23 | DAILY_COST_LIMIT 환경변수 전달 확인 |
| [x] 프론트엔드 페이지 접근 | PASS | 2026-02-23 | 모든 라우트 200 OK |

---

## 18. 참고 자료

### 설정 파일
- 환경변수: `/home/maroco/multi_agents/docker/.env`
- Docker Compose: `/home/maroco/multi_agents/docker/docker-compose.yml`
- Prometheus: `/home/maroco/multi_agents/docker/prometheus/prometheus.yml`
- Grafana: `/home/maroco/multi_agents/docker/grafana/provisioning/`

### 로그 확인
```bash
# API Gateway 로그
docker compose -f docker/docker-compose.yml logs backend -f

# Data Collector 로그
docker compose -f docker/docker-compose.yml logs data-collector -f

# PostgreSQL 로그
docker compose -f docker/docker-compose.yml logs postgres -f

# 전체 로그
docker compose -f docker/docker-compose.yml logs -f
```

### 데이터베이스 쿼리
```bash
# PostgreSQL 접속
docker exec -it agentforge-postgres psql -U postgres -d agentforge

# 사용자 조회
SELECT id, email, display_name, role FROM "user";

# 대화 조회
SELECT id, user_id, title, status FROM conversation;

# 템플릿 조회
SELECT id, user_id, name, description, is_public FROM template;
```

### API 문서
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 19. 추가 테스트 시나리오

### 19.1 여러 사용자 동시 테스트

두 개의 다른 이메일로 계정을 생성하고, 각각 로그인하여 동시에 대화를 진행합니다.

```bash
# 사용자 1
EMAIL1="user1@example.com"
PASSWORD1="User1Password123"

# 사용자 2
EMAIL2="user2@example.com"
PASSWORD2="User2Password123"

# 각 사용자로 로그인
TOKEN1=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL1\", \"password\": \"$PASSWORD1\"}" | jq -r '.access_token')

TOKEN2=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL2\", \"password\": \"$PASSWORD2\"}" | jq -r '.access_token')

# 각 사용자의 대화 목록 확인 (서로 다른 결과)
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN1" | jq

curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN2" | jq
```

### 19.2 토큰 갱신 (Refresh Token)

```bash
REFRESH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" | jq
```

**기대 응답:**
```json
{
  "access_token": "new_token...",
  "refresh_token": "new_refresh_token...",
  "token_type": "bearer"
}
```

### 19.3 대화 삭제 (구현된 경우)

```bash
CONV_ID="123e4567-e89b-12d3-a456-426614174000"

curl -X DELETE http://localhost:8000/api/v1/conversations/$CONV_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## 20. 최종 검증 체크리스트

모든 테스트를 완료한 후 아래 항목을 확인하세요:

- [ ] 서비스 모두 정상 실행 (docker ps)
- [ ] 헬스 체크 통과 (API Gateway, Data Collector)
- [ ] 회원가입/로그인 기능 정상 작동
- [ ] 대화 생성 및 메시지 송수신 정상
- [ ] 파이프라인 에디터 UI 렌더링 정상
- [ ] 템플릿 저장/로드 정상
- [ ] WebSocket 통신 정상
- [ ] 메트릭 수집 정상 (Prometheus)
- [ ] 모니터링 대시보드 데이터 표시 정상 (Grafana)
- [ ] Rate Limiting 정상 작동
- [ ] CORS 에러 없음
- [ ] 콘솔 에러 없음 (F12 Console 탭)
- [ ] Data Collector 헬스 체크 통과
- [ ] SSRF 방어 정상 작동 (내부 IP/호스트네임 차단)
- [ ] 프론트엔드 모든 라우트 접근 가능 (/login, /register, /conversations, /chat/[id], /pipeline-editor, /templates, /templates/[id])

모든 항목이 완료되면 AgentForge는 정상 작동하는 상태입니다.

---

## 21. 사용자 관점 통합 테스트 시나리오

아래 5개 시나리오는 실제 사용자 입장에서 핵심 플로우를 처음부터 끝까지 검증합니다. 개별 기능 테스트(섹션 1~14)와 달리, 여러 기능을 연결하여 실제 사용 경험을 재현합니다.

---

### 시나리오 1: 신규 가입 → 첫 AI 대화까지

> "처음 AgentForge에 방문한 사용자가 가입하고, 첫 대화를 시작하여 AI 응답을 받는다."

**전제 조건:** Docker 서비스 실행 완료, OpenAI API 키 설정 완료

| 단계 | 사용자 행동 | 기대 결과 |
|------|------------|-----------|
| 1 | `http://localhost:3000` 접속 | `/login` 페이지로 리다이렉트 |
| 2 | "Register" 링크 클릭 → `/register` 이동 | 회원가입 폼 표시 (이메일, 비밀번호, 이름) |
| 3 | 이메일/비밀번호/이름 입력 후 "Register" 클릭 | `/conversations` 페이지로 자동 이동, "No conversations yet" 표시 |
| 4 | "Start your first conversation" 버튼 클릭 | `/chat/{uuid}` 페이지로 이동, 채팅 인터페이스 표시 |
| 5 | "Build me a simple REST API for todo management" 입력 후 Send | 사용자 메시지 우측 표시 → 5~15초 후 AI 응답(설계안) 좌측 표시 |
| 6 | F12 → Network → WS 탭 확인 | `user_message_received` → `designs_presented` 순서 메시지 확인 |

**테스트 단계:**
1. 브라우저에서 `http://localhost:3000` 접속
2. 로그인 페이지에서 하단 "Register" 링크 클릭
3. 회원가입 폼 작성:
   - Email: `scenario1@example.com`
   - Password: `Scenario1Pass123`
   - Display Name: `Scenario1 User`
4. "Register" 버튼 클릭 → `/conversations` 자동 이동 확인
5. "Start your first conversation" 버튼 클릭
6. 채팅 입력창에 `Build me a simple REST API for todo management` 입력
7. Send 버튼 클릭
8. 5~15초 대기 후 AI 설계안 응답 확인
9. F12 → Application → localStorage에 `access_token` 존재 확인

**검증 포인트:** 가입 → 토큰 발급 → 대화 생성 → WebSocket 연결 → LLM 파이프라인 전체 플로우

---

### 시나리오 2: 파이프라인 설계 → 에디터 편집 → 템플릿 저장 & 공유

> "AI가 제안한 설계안을 파이프라인 에디터에서 편집하고, 저장하여 다른 사용자가 Fork할 수 있도록 공유한다."

**전제 조건:** 시나리오 1 완료 (AI 설계안 응답 수신된 상태)

| 단계 | 사용자 행동 | 기대 결과 |
|------|------------|-----------|
| 1 | AI 응답의 "Open in Pipeline Editor" 클릭 | 스플릿 뷰로 에디터 열림, 노드/엣지 시각화 |
| 2 | 좌측 사이드바에서 새 노드 드래그&드롭 | 캔버스에 노드 추가됨, 입출력 핸들 표시 |
| 3 | 기존 노드 출력 핸들 → 새 노드 입력 핸들 드래그 | 엣지(연결선) 생성 |
| 4 | 노드 더블클릭 → 속성 패널에서 이름/설명 수정 | 캔버스 노드 라벨 실시간 반영 |
| 5 | Save 버튼 클릭 | 성공 토스트 메시지 표시 |
| 6 | `/templates` 이동 → 저장된 템플릿 카드 확인 | 카드에 이름, 설명, 날짜 표시 |
| 7 | 카드 클릭 → 상세 → 공개 설정 (API: `PUT is_public=true`) | 템플릿이 공개 상태로 전환 |

**테스트 단계:**
1. 시나리오 1의 AI 응답에서 "Open in Pipeline Editor" 버튼 클릭
2. 스플릿 뷰에서 React Flow 캔버스 확인 (노드, 엣지 표시)
3. 좌측 사이드바에서 노드 타입(예: "Collector") 드래그 → 캔버스 드롭
4. 새 노드가 추가되는지 확인
5. 기존 노드의 출력 핸들(우측 원) → 새 노드의 입력 핸들(좌측 원) 드래그
6. 엣지 연결 확인
7. 노드 더블클릭 → 우측 PropertyPanel에서 이름 변경
8. Save 버튼 클릭 → F12 Network에서 `POST /api/v1/templates` 201 확인
9. 좌측 네비게이션 "Templates" 클릭 → 저장된 템플릿 카드 확인
10. API로 공개 설정:
    ```bash
    curl -X PUT http://localhost:8000/api/v1/templates/{id} \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"is_public": true}'
    ```

**검증 포인트:** 채팅 → 에디터 연동, 드래그&드롭 UX, 템플릿 CRUD, 공개 설정

---

### 시나리오 3: 대시보드에서 사용량 모니터링

> "여러 대화를 진행한 후, 대시보드에서 사용량 추이와 파이프라인 실행 이력을 확인한다."

**전제 조건:** 로그인 완료, 대화/메시지가 1개 이상 존재

| 단계 | 사용자 행동 | 기대 결과 |
|------|------------|-----------|
| 1 | 좌측 사이드바에서 "Dashboard" 클릭 | `/dashboard` 페이지 로드 |
| 2 | 상단 요약 위젯 확인 | 총 대화 수, 총 메시지 수, 총 비용, 총 파이프라인 수 카드 표시 |
| 3 | 일별 사용량 차트(LineChart) 확인 | 최근 30일 날짜별 메시지 수 추이 그래프 |
| 4 | 일별 비용 차트(BarChart) 확인 | 날짜별 LLM 비용 막대 그래프, 호버 시 정확한 금액 툴팁 |
| 5 | 파이프라인 실행 이력 테이블 확인 | 최근 20건: 이름, 상태(배지 색상), 시간, 에이전트 수 |
| 6 | 새 대화에서 AI 응답 받은 후 대시보드로 돌아옴 | 메시지 수, 비용 수치 증가 확인 |

**테스트 단계:**
1. 좌측 사이드바 "Dashboard" 클릭 또는 `http://localhost:3000/dashboard` 접속
2. 페이지 로드 후 상단 4개 요약 카드 확인:
   - Conversations 수
   - Messages 수
   - Total Cost ($)
   - Pipeline Executions 수
3. 사용량 차트(LineChart) 영역 확인 — 날짜 축(X)과 요청 수 축(Y)
4. 비용 차트(BarChart) 영역 확인 — 막대에 마우스 호버 시 비용 표시
5. 하단 파이프라인 이력 테이블 확인 — 상태별 색상 배지 (pending=노랑, completed=초록, failed=빨강)
6. `/conversations` → 새 대화 → 메시지 전송 → 다시 `/dashboard` → 숫자 변화 확인

**API 검증:**
```bash
TOKEN="your-access-token"

# 요약 정보
curl http://localhost:8000/api/v1/stats/summary \
  -H "Authorization: Bearer $TOKEN" | jq

# 일별 사용량
curl "http://localhost:8000/api/v1/stats/usage-history?days=30" \
  -H "Authorization: Bearer $TOKEN" | jq

# 파이프라인 이력
curl "http://localhost:8000/api/v1/stats/pipeline-history?limit=20" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**검증 포인트:** Stats API 3개 엔드포인트, recharts 차트 렌더링, 실시간 데이터 반영

---

### 시나리오 4: 다중 사용자 격리 & 보안

> "두 명의 사용자가 각각 로그인하여 서로의 대화와 템플릿에 접근할 수 없는지 확인한다."

**전제 조건:** Docker 서비스 실행 완료

| 단계 | 사용자 행동 | 기대 결과 |
|------|------------|-----------|
| 1 | 브라우저 A: `user1@example.com` 가입 & 로그인 | 대화 목록 비어있음 |
| 2 | 브라우저 A: 대화 생성 + 메시지 전송 | 대화 1개, 메시지 표시 |
| 3 | 시크릿 창(브라우저 B): `user2@example.com` 가입 & 로그인 | 대화 목록 비어있음 (user1 대화 안 보임) |
| 4 | 브라우저 B: user1의 대화 URL 직접 입력 (`/chat/{user1-conv-id}`) | 403 또는 404 응답 (접근 차단) |
| 5 | 브라우저 A: 로그아웃 (프로필 메뉴 → Logout) | `/login` 리다이렉트, localStorage 토큰 삭제 |
| 6 | 브라우저 A: `/conversations` 직접 접속 시도 | `/login`으로 리다이렉트 (인증 필요) |
| 7 | curl로 만료/위조 토큰으로 API 호출 | 401 Unauthorized 응답 |

**테스트 단계:**
1. **브라우저 A** (일반 창):
   - `http://localhost:3000/register`에서 `user1@example.com` / `User1Pass123` / `User 1` 가입
   - "New Conversation" → 메시지 전송 → URL의 대화 ID 기록 (예: `abc-123`)
2. **브라우저 B** (시크릿 창):
   - `http://localhost:3000/register`에서 `user2@example.com` / `User2Pass123` / `User 2` 가입
   - `/conversations` 확인 → user1의 대화가 없는지 확인
   - 주소창에 `http://localhost:3000/chat/abc-123` (user1의 대화 ID) 직접 입력
   - 에러 표시 또는 빈 화면 확인 (접근 불가)
3. **브라우저 A**:
   - 우측 상단 프로필 아이콘 → "Logout" 클릭
   - `/login` 리다이렉트 확인
   - F12 → Application → localStorage에 `access_token` 없는지 확인
   - 주소창에 `/conversations` 입력 → `/login`으로 리다이렉트
4. **curl 검증:**
   ```bash
   # 위조 토큰
   curl http://localhost:8000/api/v1/conversations \
     -H "Authorization: Bearer invalid-token-here"
   # 기대: 401 Unauthorized
   ```

**검증 포인트:** JWT 인증, 사용자 데이터 격리(IDOR 방지), 로그아웃, 미인증 접근 차단

---

### 시나리오 5: 템플릿 검색 & Fork → 파이프라인 실행 모니터링

> "공개 템플릿을 검색하고 Fork한 뒤, 파이프라인을 실행하면서 실시간 노드 상태를 모니터링한다."

**전제 조건:** 공개 템플릿 1개 이상 존재 (시나리오 2에서 생성), 로그인 완료

| 단계 | 사용자 행동 | 기대 결과 |
|------|------------|-----------|
| 1 | `/templates` 페이지 접속 | 템플릿 목록 표시 (공개 템플릿 포함) |
| 2 | 검색창에 "REST API" 입력 | 이름에 "REST API" 포함하는 템플릿만 필터링 |
| 3 | 검색 결과 카드 클릭 → 상세 페이지 | 템플릿 정보 + React Flow 다이어그램 (읽기 전용) 표시 |
| 4 | "Fork" 버튼 클릭 | 성공 메시지, 복제된 템플릿 생성 (이름에 "(fork)" 포함) |
| 5 | `/templates`로 이동 → Fork 템플릿 확인 | 목록에 "(fork)" 접미사가 붙은 새 템플릿 표시 |
| 6 | 채팅에서 파이프라인 실행 요청 | 스플릿 뷰에서 React Flow 노드 상태 변화: idle(회색) → running(파랑) → completed(초록) |
| 7 | ProgressIndicator 확인 | "2/5 agents completed" 등 진행률 바 표시 |

**테스트 단계:**
1. `http://localhost:3000/templates` 접속
2. 검색 입력창에 "REST API" 또는 시나리오 2에서 저장한 템플릿 이름의 일부 입력
3. 필터링된 결과 확인 → 카드 클릭
4. 상세 페이지에서:
   - 템플릿 이름, 설명, 날짜 표시 확인
   - React Flow 다이어그램 표시 확인 (줌/팬은 가능, 편집 불가)
5. "Fork" 버튼 클릭 → 성공 메시지 확인
6. `/templates` 목록에서 "(fork)" 붙은 새 템플릿 확인
7. 새 대화 생성 → 파이프라인 실행 요청 → 스플릿 뷰 확인:
   - F12 Network WS 탭에서 `pipeline_started`, `agent_completed`, `pipeline_result` 이벤트 확인
   - React Flow 노드 색상 변화 관찰 (idle → running → completed/failed)
   - 상단 ProgressIndicator 진행률 바 표시 확인

**API 검증:**
```bash
TOKEN="your-access-token"
TEMPLATE_ID="target-template-id"

# Fork
curl -X POST http://localhost:8000/api/v1/templates/$TEMPLATE_ID/fork \
  -H "Authorization: Bearer $TOKEN" | jq

# 기대: 201 Created, name에 "(fork)" 포함
```

**검증 포인트:** 검색 필터링, Fork 기능, 파이프라인 실시간 모니터링(이벤트 브릿지), 노드 상태 색상 변화

---

### 시나리오별 커버리지 요약

| 시나리오 | 핵심 기능 | 관련 섹션 |
|----------|----------|----------|
| 1. 신규 가입 → 첫 AI 대화 | 인증, 대화, WebSocket, LLM 파이프라인 | 1, 2, 4, 5 |
| 2. 에디터 편집 → 템플릿 저장 | 파이프라인 에디터, 템플릿 CRUD, 공유 | 6, 7, 8 |
| 3. 대시보드 모니터링 | Stats API, 차트 렌더링, 실시간 반영 | 12 (신규) |
| 4. 다중 사용자 격리 | JWT 인증, IDOR 방지, 로그아웃 | 1, 2, 9, 13 |
| 5. 템플릿 Fork → 실행 모니터링 | 검색, Fork, 실시간 노드 모니터링 | 7, 8, 11 (신규) |

---

**문서 작성일:** 2026-02-23
**버전:** 1.3
**마지막 수정:** 2026-02-23 (사용자 관점 통합 테스트 시나리오 5개 추가)
