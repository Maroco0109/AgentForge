# AgentForge 종합 문서화 설계

**날짜**: 2026-02-22
**상태**: 승인됨
**대상 독자**: 포트폴리오 면접관 + 오픈소스 기여자
**언어**: 한국어

---

## 1. 루트 README.md 전면 개편

### 새 구조

1. **헤더**: 프로젝트명 + 한줄 소개 + CI 배지 (backend-test, frontend-build, e2e, license)
2. **핵심 차별점**: 4가지 (심층 토론, Multi-LLM, 적법성 검증, 한국어 지원)
3. **아키텍처 다이어그램**: 전체 서비스 반영 (Prometheus/Grafana, E2E 포함)
4. **기술 스택**: 모니터링 행 추가 (Prometheus, Grafana)
5. **프로젝트 구조**: monitoring, e2e/ 디렉토리 반영
6. **구현 진행 상황**: Phase 1~8 전부 완료 + 모니터링/LLM 테스트/E2E CI 추가
7. **시작하기**: Docker 실행 (전체 포트), 로컬 개발, 환경변수 표
8. **테스트**: 단위/통합/E2E/LLM 통합 분리 설명
9. **CI/CD**: 6개 체크 (e2e 추가)
10. **모니터링**: Prometheus/Grafana 접속법, 대시보드 패널
11. **로드맵**: ROADMAP.md 링크
12. **기여 가이드**: 간단한 기여 절차
13. **라이선스**: MIT

### 변경 이유
- Phase 2B~8이 "예정"으로 표시 → 전부 "완료"로 업데이트
- 모니터링, E2E CI, LLM 통합 테스트 등 최근 인프라 미반영
- 환경변수 설명 부재

---

## 2. 폴더별 README (4개)

### 2.1 `backend/README.md`
- 모듈 설명: gateway, discussion, pipeline, shared
- 모듈간 의존성 다이어그램
- 환경변수 표
- 실행 방법 (로컬)
- 테스트 실행법
- API 엔드포인트 요약 표

### 2.2 `data-collector/README.md`
- 아키텍처: Compliance → Collectors → Processing 파이프라인
- 모듈 설명 (compliance/, collectors/, processing/)
- SSRF 방어 메커니즘
- 환경변수 / 실행법 / 테스트
- API 엔드포인트 표

### 2.3 `frontend/README.md`
- 기존 Next.js 기본 README → 프로젝트 맞춤 교체
- 페이지 구조 (app/ 라우팅)
- 주요 컴포넌트 설명
- WebSocket 연결 흐름
- React Flow 파이프라인 에디터
- 환경변수 / 실행법 / 빌드

### 2.4 `docker/README.md`
- 서비스 구성 표 (7개 서비스)
- 포트 매핑 표
- docker-compose.yml vs docker-compose.prod.yml 차이
- 모니터링 접속 (Prometheus, Grafana)
- 트러블슈팅

---

## 3. ROADMAP.md

### 3.1 테스트 강화 계획
- E2E 테스트 활성화 (프론트엔드 페이지 구현 후 .skip 해제)
- 부하 테스트 (Locust/k6)
- 보안 테스트 (OWASP ZAP)
- LLM 통합 테스트 확장

### 3.2 인프라 개선 계획
- Kubernetes 마이그레이션
- Grafana Alert Rules
- CI 캐시 최적화
- 프로덕션 로깅 (ELK/Loki)

### 3.3 기능 구현 계획
- 프론트엔드 페이지 분리 (/login, /register, /conversations 등)
- 사용자 대시보드 (API 사용량, 비용)
- 템플릿 마켓플레이스
- 실시간 파이프라인 모니터링

### 3.4 코드 품질 개선
- 프론트엔드 테스트 (Jest + React Testing Library)
- Alembic 마이그레이션 자동화
- API 문서 자동 생성 (OpenAPI → Redoc)

---

## 4. 구현 순서

```
1. 루트 README.md 전면 개편
2. backend/README.md 작성
3. data-collector/README.md 작성
4. frontend/README.md 작성
5. docker/README.md 작성
6. ROADMAP.md 작성
7. 커밋 + PR
```

## 5. 파일 목록

| 파일 | 작업 |
|------|------|
| `README.md` | 전면 개편 |
| `backend/README.md` | 새로 작성 |
| `data-collector/README.md` | 새로 작성 |
| `frontend/README.md` | 교체 |
| `docker/README.md` | 새로 작성 |
| `ROADMAP.md` | 새로 작성 |
