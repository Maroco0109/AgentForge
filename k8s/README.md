# AgentForge Kubernetes Deployment

Docker Compose 기반 AgentForge를 Kubernetes 클러스터에 배포하기 위한 매니페스트입니다.

## 사전 요구사항

- `kubectl` CLI (v1.28+)
- Kubernetes 클러스터 (v1.28+)
- NGINX Ingress Controller (`kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml`)
- Container 이미지 빌드 완료 (agentforge-backend, agentforge-frontend, agentforge-collector)

## 이미지 빌드

```bash
# Backend
docker build -f docker/Dockerfile.backend.prod -t agentforge-backend:latest ./backend

# Frontend
docker build -f docker/Dockerfile.frontend.prod \
  --build-arg NEXT_PUBLIC_API_URL=https://your-domain.com/api \
  --build-arg NEXT_PUBLIC_WS_URL=wss://your-domain.com/ws \
  -t agentforge-frontend:latest ./frontend

# Data Collector
docker build -f docker/Dockerfile.collector.prod -t agentforge-collector:latest ./data-collector
```

## 시크릿 생성

```bash
# 1. 시크릿 파일 복사
cp k8s/secrets.yaml.example k8s/secrets.yaml
cp k8s/monitoring/monitoring-secret.yaml.example k8s/monitoring/monitoring-secret.yaml

# 2. base64 인코딩된 값으로 교체
echo -n 'your-secret-key' | base64
# 출력된 값을 secrets.yaml에 붙여넣기

# 3. 시크릿 적용
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/monitoring/monitoring-secret.yaml
```

## 배포 순서

```bash
# 1. 네임스페이스 + 시크릿 (먼저 적용)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/monitoring/monitoring-secret.yaml

# 2. 전체 매니페스트 배포 (kustomize)
kubectl apply -k k8s/

# 3. PostgreSQL 준비 대기
kubectl wait --for=condition=ready pod/postgres-0 -n agentforge --timeout=120s

# 4. DB 마이그레이션 Job 완료 대기
kubectl wait --for=condition=complete job/alembic-migration -n agentforge --timeout=120s

# 5. 전체 서비스 상태 확인
kubectl get pods -n agentforge
kubectl get jobs -n agentforge
kubectl get svc -n agentforge
```

## 스케일링

```bash
# 수동 스케일링
kubectl scale deployment backend -n agentforge --replicas=3

# HPA 확인 (backend은 자동 스케일링)
kubectl get hpa -n agentforge

# HPA 상세 정보
kubectl describe hpa backend-hpa -n agentforge
```

## 트러블슈팅

```bash
# Pod 로그 확인
kubectl logs -f deployment/backend -n agentforge
kubectl logs -f deployment/frontend -n agentforge
kubectl logs -f deployment/data-collector -n agentforge

# Pod 상태 확인
kubectl describe pod <pod-name> -n agentforge

# 마이그레이션 Job 로그
kubectl logs job/alembic-migration -n agentforge

# 서비스 연결 테스트
kubectl run debug --rm -it --image=busybox -n agentforge -- wget -qO- http://backend:8000/api/v1/health

# Ingress 상태
kubectl describe ingress agentforge-ingress -n agentforge
```

## 로컬 테스트 (minikube)

```bash
# minikube 시작
minikube start

# Ingress addon 활성화
minikube addons enable ingress

# 이미지 빌드 (minikube Docker 환경 사용)
eval $(minikube docker-env)
docker build -f docker/Dockerfile.backend.prod -t agentforge-backend:latest ./backend
docker build -f docker/Dockerfile.frontend.prod \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost/api \
  --build-arg NEXT_PUBLIC_WS_URL=ws://localhost/ws \
  -t agentforge-frontend:latest ./frontend
docker build -f docker/Dockerfile.collector.prod -t agentforge-collector:latest ./data-collector

# 시크릿 생성 후 배포
cp k8s/secrets.yaml.example k8s/secrets.yaml
# secrets.yaml 값 설정...
kubectl apply -f k8s/secrets.yaml
kubectl apply -k k8s/

# 접속 (minikube tunnel 필요)
minikube tunnel
```

## 관리형 서비스 전환 가이드

프로덕션 환경에서 관리형 DB/Redis 사용 시:

1. `k8s/postgres/`, `k8s/redis/` 디렉토리 삭제
2. `kustomization.yaml`에서 해당 리소스 제거
3. `secrets.yaml`의 DATABASE_URL, REDIS_URL을 관리형 서비스 엔드포인트로 변경
4. NetworkPolicy에서 postgres/redis 관련 정책 제거
