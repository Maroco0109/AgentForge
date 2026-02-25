# AgentForge 시작하기

AgentForge는 사용자 프롬프트 기반 멀티 에이전트 플랫폼입니다. 이 가이드는 로컬 환경에서 AgentForge를 실행하는 방법을 안내합니다.

## 목차

1. [사전 준비](#사전-준비)
2. [빠른 시작 (자동 설정)](#빠른-시작-자동-설정)
3. [수동 설정](#수동-설정)
4. [사용 방법](#사용-방법)
5. [API 테스트](#api-테스트)
6. [트러블슈팅](#트러블슈팅)
7. [서비스 관리](#서비스-관리)

---

## 사전 준비

### 필수 소프트웨어

1. **Docker 및 Docker Compose**
   - Docker Desktop (macOS/Windows): https://docs.docker.com/get-docker/
   - Docker Engine (Linux): https://docs.docker.com/engine/install/

   설치 확인:
   ```bash
   docker --version
   docker compose version
   ```

2. **LLM API 키** (BYOK 모드)
   - AgentForge는 BYOK(Bring Your Own Key) 모드를 지원합니다
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/settings/keys
   - Google Gemini: https://aistudio.google.com/apikey
   - 환경변수에 설정하거나, 웹 UI의 Settings 페이지에서 등록할 수 있습니다

---

## 빠른 시작 (자동 설정)

프로젝트 루트에서 다음 명령어를 실행하면 자동으로 설정됩니다:

```bash
./scripts/setup.sh
```

스크립트가 자동으로 수행하는 작업:
1. Docker 및 Docker Compose 설치 확인
2. `.env.example` → `.env` 복사 (기존 파일이 있으면 유지)
3. OpenAI API 키 입력 프롬프트
4. Docker 컨테이너 빌드 및 시작
5. 헬스체크 대기 (최대 2분)
6. 성공 메시지 및 접속 URL 출력

### 실행 예시

```bash
$ ./scripts/setup.sh

  ╔══════════════════════════════════════╗
  ║       AgentForge Setup Script        ║
  ╚══════════════════════════════════════╝

[INFO] 필수 소프트웨어 확인 중...
[OK] Docker + Docker Compose 확인 완료
[INFO] .env 파일 설정 중...
[OK] .env.example → .env 복사 완료
[WARN] OPENAI_API_KEY가 설정되지 않았습니다.
OpenAI API 키를 입력하세요 (Enter로 건너뛰기): sk-proj-xxxxx
[OK] OPENAI_API_KEY 설정 완료
[INFO] Docker 서비스 빌드 및 시작 중... (처음 실행 시 3~5분 소요)
[INFO] 서비스 헬스체크 대기 중...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AgentForge가 성공적으로 시작되었습니다!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Frontend:       http://localhost:3000
  Backend API:    http://localhost:8000/api/v1/health
  Data Collector: http://localhost:8001/health
```

설정이 완료되면 브라우저에서 http://localhost:3000 을 열어 사용할 수 있습니다.

---

## 수동 설정

자동 스크립트를 사용하지 않고 수동으로 설정하려면:

### 1. 환경 변수 설정

```bash
cd docker
cp .env.example .env
```

`.env` 파일을 편집하여 최소한 다음 항목을 설정하세요:

```env
# 필수: OpenAI API 키
OPENAI_API_KEY=sk-proj-your-actual-key-here

# 권장: 프로덕션 환경에서는 SECRET_KEY 변경
SECRET_KEY=$(openssl rand -hex 32)

# BYOK 암호화 키 (API 키 등록 시 필수)
ENCRYPTION_KEY=$(python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
```

### 2. Docker 컨테이너 시작

```bash
cd docker
docker compose up --build -d
```

처음 실행 시 이미지 빌드로 3~5분 소요될 수 있습니다.

### 3. 서비스 확인

모든 서비스가 정상적으로 시작되었는지 확인:

```bash
# Backend API
curl http://localhost:8000/api/v1/health

# Data Collector
curl http://localhost:8001/health

# Frontend (브라우저)
open http://localhost:3000
```

---

## 사용 방법

### 1. 회원가입

브라우저에서 http://localhost:3000 접속 후:

1. "회원가입" 버튼 클릭
2. 이메일, 표시 이름(display_name), 비밀번호 입력
   - **비밀번호 요구사항**: 8자 이상, 대문자 1개 이상, 숫자 1개 이상
   - 예시: `Password123`
3. 가입 완료 후 자동 로그인

### 2. 로그인

이미 계정이 있다면:

1. 이메일과 비밀번호 입력
2. 로그인 버튼 클릭
3. JWT 토큰이 자동으로 브라우저에 저장됨

### 3. 채팅 (Discussion Engine)

로그인 후 메인 화면에서:

1. **새 대화 시작** 버튼 클릭
2. 채팅창에 프롬프트 입력
   - 예시: "Python으로 간단한 웹 크롤러를 만들어줘"
3. 실시간으로 AI 응답 수신 (WebSocket)
4. 대화 기록은 자동 저장됨

### 4. 파이프라인 실행 (고급)

복잡한 작업을 여러 단계로 나누어 실행:

1. "새 파이프라인" 버튼 클릭
2. 파이프라인 이름과 설명 입력
3. 노드 추가:
   - **Analyzer**: 프롬프트 의도 분석
   - **Designer**: 설계 생성
   - **Critic**: 설계 검토
   - **Collector**: 외부 데이터 수집
4. 노드 연결 (드래그 앤 드롭)
5. "실행" 버튼으로 파이프라인 시작
6. 각 노드의 실행 결과를 실시간으로 확인

### 5. BYOK API 키 등록

자신의 LLM API 키를 등록하여 파이프라인을 실행할 수 있습니다:

1. 좌측 사이드바에서 **Settings** 클릭
2. Provider 카드에서 **Add Key** 클릭 (OpenAI / Anthropic / Google)
3. API 키 입력 후 등록
4. 자동 검증 → 상태 배지 표시 (Valid / Invalid)
5. 최소 1개의 유효한 키가 등록되면 파이프라인 실행 가능

---

## API 테스트

curl을 사용한 API 직접 호출 예시입니다.

### 헬스체크

```bash
# Backend
curl http://localhost:8000/api/v1/health

# Data Collector
curl http://localhost:8001/health
```

응답 예시:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 회원가입

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123",
    "display_name": "테스트유저"
  }'
```

응답 예시:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "test@example.com",
    "display_name": "테스트유저",
    "role": "free"
  }
}
```

### 로그인

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123"
  }'
```

응답은 회원가입과 동일한 형식입니다.

### 대화 생성 (인증 필요)

```bash
# 먼저 토큰 저장
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 대화 생성
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "첫 번째 대화"
  }'
```

응답 예시:
```json
{
  "id": "uuid-here",
  "title": "첫 번째 대화",
  "user_id": "user-uuid",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 파이프라인 직접 실행 (인증 필요)

```bash
curl -X POST http://localhost:8000/api/v1/pipelines/execute-direct \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "design": {
      "design_name": "간단한 분석 파이프라인",
      "agents": [
        {"name": "analyzer", "role": "intent_analyzer", "model_hint": "auto"},
        {"name": "designer", "role": "design_generator", "model_hint": "auto"}
      ],
      "edges": [
        {"from_agent": "analyzer", "to_agent": "designer"}
      ]
    },
    "user_prompt": "Python으로 간단한 웹 크롤러를 만들어줘"
  }'
```

### 외부 데이터 수집 (Data Collector)

```bash
curl -X POST http://localhost:8001/collect \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "format": "text"
  }'
```

응답 예시:
```json
{
  "content": "수집된 텍스트 내용...",
  "metadata": {
    "url": "https://example.com",
    "collected_at": "2024-01-15T10:30:00Z",
    "content_type": "text/html"
  }
}
```

---

## 트러블슈팅

### 1. 포트 충돌

**증상**: `Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use`

**해결**:
```bash
# 충돌하는 포트 찾기
sudo lsof -i :8000
sudo lsof -i :3000
sudo lsof -i :5432

# 프로세스 종료 후 재시작
docker compose down
docker compose up -d
```

### 2. 데이터베이스 연결 실패

**증상**: Backend 로그에 `could not connect to server: Connection refused`

**해결**:
```bash
# PostgreSQL 컨테이너 상태 확인
docker compose ps postgres

# PostgreSQL 로그 확인
docker compose logs postgres

# 컨테이너 재시작
docker compose restart postgres backend
```

### 3. LLM API 키 오류

**증상**: 채팅 시 "Invalid API key" 또는 "No API key provided"

**해결**:
```bash
# .env 파일에서 API 키 확인
cat docker/.env | grep OPENAI_API_KEY

# API 키 재설정
cd docker
nano .env  # OPENAI_API_KEY=sk-proj-your-key-here

# 컨테이너 재시작 (환경변수 적용)
docker compose down
docker compose up -d
```

### 4. 프론트엔드 빌드 오류

**증상**: Frontend 컨테이너가 시작되지 않음

**해결**:
```bash
# 빌드 캐시 삭제 후 재빌드
docker compose down
docker compose build --no-cache frontend
docker compose up -d
```

### 5. 헬스체크 타임아웃

**증상**: `setup.sh` 실행 시 "서비스가 시간 내에 시작되지 않았습니다"

**해결**:
```bash
# 각 서비스 로그 확인
docker compose logs backend
docker compose logs data-collector
docker compose logs postgres
docker compose logs redis

# 문제 서비스만 재시작
docker compose restart <service-name>
```

### 6. WebSocket 연결 실패

**증상**: 채팅창에서 "Connection failed" 메시지

**해결**:
```bash
# CORS 설정 확인
cat docker/.env | grep CORS_ORIGINS

# WebSocket URL 확인
cat docker/.env | grep NEXT_PUBLIC_WS_URL

# Backend 재시작
docker compose restart backend
```

### 7. 권한 오류 (Linux)

**증상**: `permission denied while trying to connect to the Docker daemon socket`

**해결**:
```bash
# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 재로그인 또는 그룹 활성화
newgrp docker

# Docker 재시작
sudo systemctl restart docker
```

---

## 서비스 관리

### 서비스 중지

```bash
cd docker
docker compose down
```

데이터까지 삭제하려면 (주의: 모든 대화 및 파이프라인 삭제됨):
```bash
docker compose down -v
```

### 서비스 재시작

```bash
cd docker
docker compose restart
```

특정 서비스만 재시작:
```bash
docker compose restart backend
docker compose restart frontend
```

### 로그 확인

모든 서비스 로그:
```bash
docker compose logs -f
```

특정 서비스 로그:
```bash
docker compose logs -f backend
docker compose logs -f data-collector
```

### 컨테이너 상태 확인

```bash
docker compose ps
```

예상 출력:
```
NAME                    STATUS          PORTS
agentforge-backend      Up 5 minutes    0.0.0.0:8000->8000/tcp
agentforge-frontend     Up 5 minutes    0.0.0.0:3000->3000/tcp
agentforge-postgres     Up 5 minutes    5432/tcp
agentforge-redis        Up 5 minutes    6379/tcp
agentforge-collector    Up 5 minutes    0.0.0.0:8001->8001/tcp
```

### 데이터베이스 백업

```bash
# PostgreSQL 데이터 백업
docker compose exec postgres pg_dump -U postgres agentforge > backup.sql

# 복원
docker compose exec -T postgres psql -U postgres agentforge < backup.sql
```

### 컨테이너 내부 접속

디버깅이 필요한 경우:

```bash
# Backend 컨테이너
docker compose exec backend bash

# PostgreSQL
docker compose exec postgres psql -U postgres agentforge

# Redis
docker compose exec redis redis-cli
```

---

## 다음 단계

AgentForge를 성공적으로 실행했다면:

1. **API 문서 확인**: http://localhost:8000/docs (Swagger UI)
2. **대시보드 확인**: http://localhost:3000/dashboard (사용량 차트, 파이프라인 이력)
3. **아키텍처 이해**: `docs/phase-*.md` 문서 읽기
4. **테스트 실행**: `cd backend && python -m pytest ../tests/ -v` 로컬 테스트 실행
5. **파이프라인 에디터**: React Flow 기반 시각적 파이프라인 편집기 사용
6. **BYOK 설정**: Settings 페이지에서 LLM API 키 등록 (http://localhost:3000/settings)

문제가 발생하면 GitHub Issues에 등록해주세요:
https://github.com/Maroco0109/AgentForge/issues

---

**Happy Building with AgentForge! 🚀**
