# Docker — 컨테이너 오케스트레이션

## 개요

AgentForge의 개발 및 프로덕션 환경을 위한 Docker Compose 설정입니다. 7개의 서비스(프론트엔드, 백엔드, 데이터 수집기, PostgreSQL, Redis, Prometheus, Grafana)를 오케스트레이션하며, 헬스체크와 의존성 관리를 통해 안정적인 컨테이너 실행 환경을 제공합니다.

## 서비스 구성

| Service | Image | Port | Healthcheck | Dependencies |
|---------|-------|------|-------------|--------------|
| frontend | Node 20 | 3000 | - | backend |
| backend | Python 3.11 | 8000 | GET /api/v1/health | postgres, redis |
| data-collector | Python 3.11 | 8001 | GET /api/v1/health | postgres, redis |
| postgres | postgres:16-alpine | 5432 | pg_isready | - |
| redis | redis:7-alpine | 6379 | redis-cli ping | - |
| prometheus | prom/prometheus:v2.51.0 | 9090 | - | backend |
| grafana | grafana/grafana:10.4.0 | 3001 | - | prometheus |

## 빠른 시작

```bash
# 환경변수 파일 생성
cp .env.example .env

# 컨테이너 시작
docker compose up -d
```

### 접속 URL

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8000/docs |
| 데이터 수집기 | http://localhost:8001/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |

## 개발 vs 프로덕션 환경

| Aspect | Development | Production |
|--------|-------------|------------|
| Dockerfile | 경량(reload) | 멀티스테이지, 최적화 |
| Volume | 소스코드 마운트 | 없음 (이미지 내장) |
| 환경변수 | 하드코딩 | .env 파일 |
| Restart | 없음 | unless-stopped |
| 리소스 제한 | 없음 | frontend:512M, backend:1G, collector:512M |
| 로깅 | 기본 | json-file, 10M, 3 rotation |
| Backend | uvicorn --reload | gunicorn 4 workers |
| Redis | 비밀번호 없음 | REDIS_PASSWORD 필수 |
| 모니터링 | prometheus+grafana 포함 | 외부 모니터링 사용 |

## Prometheus 설정

메트릭 수집 설정 (`prometheus/prometheus.yml`):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics

  - job_name: 'data-collector'
    static_configs:
      - targets: ['data-collector:8001']
    metrics_path: /metrics
```

## Grafana 대시보드

총 9개 패널로 구성된 모니터링 대시보드를 제공합니다:

### HTTP 메트릭
- HTTP Request Rate: 초당 요청 수
- HTTP Latency: p50/p95/p99 응답 시간
- Error Rate: 4xx/5xx 에러 비율

### LLM 메트릭
- LLM Token Usage: 토큰 사용량 추이
- LLM Cost Tracking: API 비용 추적
- LLM Request Latency: LLM 요청 지연시간

### 파이프라인 메트릭
- Pipeline Execution Status: 실행 성공/실패 비율
- Pipeline Duration Distribution: 실행 시간 분포
- Active WebSocket Connections: 활성 연결 수

**접속 정보:**
- URL: http://localhost:3001
- 기본 계정: admin / admin

## 환경변수

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 아래 변수들을 설정합니다:

### Database
```env
POSTGRES_DB=agentforge
POSTGRES_USER=agentforge
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://agentforge:your_secure_password@postgres:5432/agentforge
```

### Redis
```env
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your_redis_password  # 프로덕션 필수
```

### Backend
```env
SECRET_KEY=your_secret_key_here
DEBUG=false
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Frontend
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### LLM API Keys
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Cost Limit
```env
DAILY_COST_LIMIT=10.00
```

## 트러블슈팅

### frontend/.next 권한 문제
Docker 빌드 후 `.next` 디렉토리가 root 소유가 될 수 있습니다:

```bash
sudo chown -R $(whoami) frontend/.next
```

### 백엔드 시작 실패
로그를 확인하여 원인을 파악합니다:

```bash
docker compose logs backend
```

### 데이터베이스 마이그레이션
백엔드 컨테이너 시작 시 `entrypoint.sh`가 자동으로 `alembic upgrade head`를 실행하여 DB 스키마를 최신 상태로 유지합니다. 수동 실행이 필요한 경우:

```bash
docker compose exec backend python -m alembic -c /app/backend/alembic.ini upgrade head
```

### DB 초기화
데이터베이스를 완전히 초기화하려면:

```bash
docker compose down -v
docker compose up -d
```

### 포트 충돌
포트가 이미 사용 중인 경우:

```bash
lsof -i :8000
```

## 프로덕션 실행

프로덕션 환경에서는 최적화된 설정 파일을 사용합니다:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**프로덕션 체크리스트:**
- [ ] SECRET_KEY 환경변수 설정
- [ ] REDIS_PASSWORD 설정
- [ ] DEBUG=false 확인
- [ ] CORS_ORIGINS 프로덕션 도메인 추가
- [ ] 리소스 제한 확인 (메모리/CPU)
- [ ] 로그 로테이션 설정 확인
- [ ] SSL/TLS 인증서 설정 (리버스 프록시 사용 권장)
