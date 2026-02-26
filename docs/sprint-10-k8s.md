# Sprint 10: Kubernetes 배포 매니페스트

## 개요

Docker Compose 기반 AgentForge 7개 서비스를 Kubernetes 클러스터에서 실행할 수 있도록 매니페스트를 작성하고, 필요한 코드 수정을 수행했다.

## K8s 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                  NGINX Ingress                       │
│         (cookie affinity, WebSocket support)         │
├─────────────┬───────────────┬───────────────────────┤
│   /         │   /api/       │   /ws/                │
│   ↓         │   ↓           │   ↓                   │
│ frontend:3000│ backend:8000 │ backend:8000          │
│ (2 replicas)│ (2-5, HPA)   │ (workers=1, WS safe)  │
├─────────────┴───────────────┴───────────────────────┤
│                  NetworkPolicy                       │
├──────────────────┬──────────────────────────────────┤
│  PostgreSQL      │  Redis                           │
│  StatefulSet     │  StatefulSet                     │
│  (10Gi PVC)      │  (2Gi PVC, 256MB maxmemory)     │
├──────────────────┴──────────────────────────────────┤
│  Monitoring: Prometheus (10Gi) + Grafana (5Gi)      │
└─────────────────────────────────────────────────────┘
```

## 서비스 간 통신 흐름

| 소스 | 대상 | 프로토콜 | K8s DNS |
|------|------|----------|---------|
| Ingress | frontend | HTTP | frontend.agentforge.svc.cluster.local:3000 |
| Ingress | backend | HTTP/WS | backend.agentforge.svc.cluster.local:8000 |
| backend | PostgreSQL | TCP | postgres-0.postgres.agentforge.svc.cluster.local:5432 |
| backend | Redis | TCP | redis-0.redis.agentforge.svc.cluster.local:6379 |
| backend | data-collector | HTTP | data-collector.agentforge.svc.cluster.local:8001 |
| data-collector | PostgreSQL | TCP | (동일) |
| data-collector | Redis | TCP | (동일) |
| Prometheus | backend | HTTP | /metrics 스크래핑 |
| Prometheus | data-collector | HTTP | /metrics 스크래핑 |

## 환경변수 매핑 (docker-compose → K8s)

### ConfigMap (비민감)

| 환경변수 | docker-compose | K8s ConfigMap |
|----------|---------------|---------------|
| POSTGRES_DB | `${POSTGRES_DB:?...}` | `agentforge` |
| DATA_COLLECTOR_URL | `http://data-collector:8001` | `http://data-collector.agentforge.svc.cluster.local:8001` |
| CORS_ORIGINS | `.env` | `["https://your-domain.com"]` |
| DEBUG | `false` | `false` |
| DAILY_COST_LIMIT | `.env` | `10.0` |
| AUTH_RATE_LIMIT | `.env` | `5` |
| DB_POOL_SIZE | (기본값 5) | `5` |
| DB_MAX_OVERFLOW | (기본값 10) | `10` |

### Secret (민감)

| 환경변수 | docker-compose | K8s Secret |
|----------|---------------|-----------|
| SECRET_KEY | `.env` | agentforge-secrets |
| ENCRYPTION_KEY | `.env` | agentforge-secrets |
| DATABASE_URL | `.env` + env override | agentforge-secrets |
| REDIS_URL | env override | agentforge-secrets |
| POSTGRES_USER | `${POSTGRES_USER:?...}` | agentforge-secrets |
| POSTGRES_PASSWORD | `${POSTGRES_PASSWORD:?...}` | agentforge-secrets |
| REDIS_PASSWORD | `${REDIS_PASSWORD:?...}` | agentforge-secrets |

## 주요 설계 결정

### 1. gunicorn workers=1 (Architect #2)

WebSocket ConnectionManager가 in-memory dict 기반이므로 workers > 1이면 세션이 분산되어 메시지 유실. workers=1 + HPA 수평 확장으로 보상.

**향후 개선**: Redis Pub/Sub로 WS 메시지 브로드캐스트 → workers=4 복원 가능.

### 2. Alembic Job 분리 (Architect #1)

initContainer 대신 별도 Job으로 분리하여 race condition 방지. 여러 pod가 동시에 마이그레이션을 실행하면 충돌 가능.

**배포 순서**: PostgreSQL Ready → Migration Job 완료 → Backend Deployment.

### 3. Cookie Affinity (Critic A2)

Ingress 뒤에서 ClientIP affinity는 Ingress 자체 IP로 인식되어 무효. Cookie 기반 affinity로 WebSocket 세션 유지.

### 4. NetworkPolicy (Critic A4)

최소 권한 원칙 적용:
- PostgreSQL: backend + data-collector + migration-job만 접근
- Redis: backend + data-collector만 접근
- 외부 트래픽: frontend + backend만 허용

### 5. PodDisruptionBudget (Architect #7)

backend, frontend에 PDB 적용 (minAvailable: 1). 롤링 업데이트/노드 드레인 시 서비스 가용성 보장.

## WebSocket 스케일링 전략

| 단계 | 방식 | 처리량 | 제한 |
|------|------|--------|------|
| **현재** | workers=1 + HPA (2-5 pods) | 중간 | pod간 WS 세션 격리 |
| **향후** | workers=4 + Redis Pub/Sub | 높음 | Redis 의존성 추가 |

현재 구조에서 cookie affinity로 같은 사용자의 WS 연결이 동일 pod로 라우팅되어 실용적으로 동작.

## 코드 수정 사항

| 파일 | 변경 | 이유 |
|------|------|------|
| `backend/shared/config.py` | DB_POOL_SIZE, DB_MAX_OVERFLOW 추가 | K8s 환경변수로 풀 크기 조정 |
| `backend/shared/database.py` | pool_size, max_overflow, pool_recycle, pool_pre_ping | 커넥션 풀 최적화 |
| `docker/Dockerfile.backend.prod` | workers=1, --ws-max-size | WS 호환 + 메시지 크기 제한 |
| `docker/Dockerfile.collector.prod` | HEALTHCHECK /api/v1/health | 실제 엔드포인트와 일치 |

## 파일 구조

```
k8s/
├── kustomization.yaml          # Kustomize 진입점
├── namespace.yaml              # agentforge 네임스페이스
├── configmap.yaml              # 비민감 환경변수
├── secrets.yaml.example        # 민감 환경변수 (템플릿)
├── ingress.yaml                # NGINX Ingress + cookie affinity
├── network-policy.yaml         # Pod간 접근 제어
├── backend/
│   ├── migration-job.yaml      # Alembic DB 마이그레이션
│   ├── deployment.yaml         # 2 replicas, HPA 대상
│   ├── service.yaml            # ClusterIP :8000
│   ├── hpa.yaml                # CPU 70%, 2-5 replicas
│   └── pdb.yaml                # minAvailable: 1
├── frontend/
│   ├── deployment.yaml         # 2 replicas
│   ├── service.yaml            # ClusterIP :3000
│   └── pdb.yaml                # minAvailable: 1
├── data-collector/
│   ├── deployment.yaml         # 1 replica
│   └── service.yaml            # ClusterIP :8001
├── postgres/
│   ├── statefulset.yaml        # 1 replica, 10Gi PVC
│   └── service.yaml            # Headless
├── redis/
│   ├── statefulset.yaml        # 1 replica, 2Gi PVC
│   └── service.yaml            # Headless
└── monitoring/
    ├── monitoring-secret.yaml.example
    ├── prometheus-configmap.yaml
    ├── prometheus-deployment.yaml  # + PVC 10Gi
    ├── prometheus-service.yaml
    ├── grafana-deployment.yaml     # + PVC 5Gi + provisioning
    └── grafana-service.yaml
```

## 알려진 제한사항

1. **Grafana 대시보드 JSON**: ConfigMap으로 마운트하려면 `agentforge.json`을 별도 ConfigMap으로 생성해야 함 (크기가 커서 별도 관리 권장)
2. **TLS**: cert-manager 설정은 클러스터별로 다르므로 주석 처리 상태
3. **이미지 레지스트리**: `imagePullPolicy: Always` 미설정 — 프라이빗 레지스트리 사용 시 추가 설정 필요
4. **Secrets**: `$(POSTGRES_USER)` 등 변수 참조는 K8s에서 자동 치환되지 않음 — 실제 배포 시 직접 연결 문자열 입력 필요
