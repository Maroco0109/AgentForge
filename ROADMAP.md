# AgentForge 로드맵

## 테스트 강화 계획

### E2E 테스트 활성화
- 현재 상태: auth, chat, pipeline-editor, templates 4개 테스트 스위트가 .skip 처리
- 원인: 프론트엔드에 /register, /login, /conversations, /chat/{id}, /pipeline-editor, /templates 페이지가 미구현 (SPA 구조)
- 계획: 프론트엔드 라우팅 구현 후 test.describe.skip → test.describe로 전환
- smoke test (루트 페이지 + 백엔드 헬스체크)는 현재 활성 상태

### 부하 테스트
- Locust 또는 k6로 API 성능 벤치마크
- 목표: 동시 100명 사용자, 평균 응답 시간 < 200ms
- LLM 호출 제외한 순수 API 성능 측정

### 보안 테스트
- OWASP ZAP 자동 스캔 CI 통합
- 프롬프트 인젝션 방어 효과 검증 (adversarial test suite)
- SSRF 방어 우회 시도 테스트

### LLM 통합 테스트 확장
- Anthropic Claude 실제 호출 테스트
- 에러 시나리오 (rate limit, timeout, invalid response) 테스트
- 비용 계산 정확성 검증
- 다국어 의도 분석 테스트

## 인프라 개선 계획

### Kubernetes 마이그레이션
- Docker Compose → Helm Chart 전환
- HPA (Horizontal Pod Autoscaler) 설정
- Ingress Controller + TLS 설정

### Grafana Alert Rules
- LLM 비용 임계치 알림 (일 $10 초과 시)
- API 에러율 5% 이상 알림
- 파이프라인 실패율 모니터링
- 서비스 다운 알림

### CI 캐시 최적화
- Docker layer 캐시 (GitHub Actions cache)
- pip/npm 의존성 캐시
- Playwright 브라우저 캐시
- 목표: CI 실행 시간 50% 단축

### 프로덕션 로깅
- ELK Stack 또는 Grafana Loki 도입
- 구조화된 JSON 로그 포맷
- 요청 추적 ID (correlation ID)
- 로그 레벨별 분류 (ERROR → PagerDuty 연동)

## 기능 구현 계획

### 프론트엔드 페이지 분리
- 현재: app/page.tsx 단일 SPA
- 계획: Next.js App Router 활용
  - /login — 로그인 페이지
  - /register — 회원가입 페이지
  - /conversations — 대화 목록
  - /chat/{id} — 개별 채팅
  - /pipeline-editor — 독립 파이프라인 에디터
  - /templates — 템플릿 마켓플레이스
  - /dashboard — 사용자 대시보드

### 사용자 대시보드
- API 사용량 (일별/월별 호출 수)
- LLM 비용 현황 (모델별, 일별 추이)
- 파이프라인 실행 이력 및 성공률
- API 키 관리 UI

### 템플릿 마켓플레이스
- 공개 템플릿 검색/필터/정렬
- 인기도/평점 기반 랭킹
- 카테고리별 분류 (데이터 분석, 웹 크롤링, 문서 생성 등)
- 포크/커스터마이즈/재공유

### 실시간 파이프라인 모니터링
- React Flow + WebSocket으로 에이전트 노드별 실시간 상태
- 노드 실행 진행률 애니메이션
- 실시간 로그 스트리밍
- 비용 실시간 누적 표시

## 코드 품질 개선

### 프론트엔드 테스트
- Jest + React Testing Library 도입
- 컴포넌트 단위 테스트 (ChatWindow, PipelineEditor)
- 커스텀 훅 테스트 (useFlowState, usePipelineExecution)
- 목표: 프론트엔드 커버리지 70%+

### Alembic 마이그레이션 자동화
- CI에서 자동 마이그레이션 검증
- 마이그레이션 스크립트 생성 자동화
- 롤백 테스트

### API 문서 자동 생성
- OpenAPI 스펙 → Redoc/Swagger UI
- 자동 생성된 SDK 클라이언트
- 엔드포인트별 예시 요청/응답

## 우선순위

| 순위 | 항목 | 예상 난이도 | 영향도 |
|------|------|-----------|--------|
| 1 | 프론트엔드 페이지 분리 | 중 | 높음 |
| 2 | E2E 테스트 활성화 | 낮음 | 높음 |
| 3 | Grafana Alert Rules | 낮음 | 중간 |
| 4 | 사용자 대시보드 | 중 | 높음 |
| 5 | 프론트엔드 테스트 | 중 | 중간 |
| 6 | 부하 테스트 | 낮음 | 중간 |
| 7 | API 문서 자동 생성 | 낮음 | 중간 |
| 8 | 템플릿 마켓플레이스 | 높음 | 높음 |
| 9 | Kubernetes 마이그레이션 | 높음 | 중간 |
| 10 | 프로덕션 로깅 | 중 | 중간 |
