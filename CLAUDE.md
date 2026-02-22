# AgentForge - Claude Code 프로젝트 지침

## 프로젝트 개요

사용자 프롬프트 기반 멀티 에이전트 플랫폼. 8 Phase 점진적 구현.
- **리포**: https://github.com/Maroco0109/AgentForge
- **계획 파일**: `~/.claude/plans/mossy-knitting-truffle.md` (반드시 참조)

## 필수 규칙

### 1. 계획 파일 준수 (최우선)

모든 구현은 `~/.claude/plans/mossy-knitting-truffle.md`의 Phase별 계획을 따른다.
- Phase별 구현 범위, 파일 구조, 테스트 요구사항을 반드시 확인 후 작업
- 계획에 없는 기능을 임의로 추가하지 않음
- Phase 의존성 그래프를 존중 (예: Phase 4는 Phase 3 완료 후)

### 2. GitHub Workflow Skill 활용

모든 GitHub 작업은 `github-workflow` 스킬을 따른다:
- Issue 생성 → 브랜치 생성 → 구현 → PR 생성 → CI 대기 → 리뷰 수정 → 사용자 머지
- PR 생성 시 상세 Body 템플릿 사용
- `gh pr merge` 자동 실행 금지 - 사용자 명시적 요청 시에만

### 3. CI 자동화 준수

PR 머지 전 5개 체크 전부 통과 필수:
- `backend-test`: pytest (backend + data-collector)
- `backend-lint`: ruff format + check
- `frontend-build`: Next.js 프로덕션 빌드
- `frontend-lint`: ESLint
- `claude-review`: AI 코드 리뷰 (코멘트 내용 반드시 확인)

CI 실패 시 수정 루프: 원인 분석 → 수정 → 커밋/푸시 → CI 재확인 → 반복

## 브랜치 전략

```
feat/phase-N-xxx → develop (Refs #이슈번호)
develop → main (Closes #이슈번호, E2E 완료 시)
```

- `main`: 안정 코드만
- `develop`: Phase 머지 브랜치
- 브랜치 생성은 반드시 `develop`에서 분기

## 현재 상태 (Sprint 1 완료)

| Phase | 상태 | PR |
|-------|------|-----|
| Phase 1 | ✅ 완료 | #2 (main 머지) |
| Phase 2A | ✅ 완료 | #6 (develop 머지) |
| Phase 3 | ✅ 완료 | #7 (develop 머지) |
| Phase 6 | ✅ 완료 | #8 (develop 머지) |

다음: Sprint 2 (Phase 2B + Phase 4)

## 디렉토리 구조

```
backend/           # FastAPI 백엔드 (gateway, discussion, pipeline, shared)
frontend/          # Next.js 14 App Router
data-collector/    # 독립 마이크로서비스 (FastAPI)
tests/             # 통합 테스트 (unit, integration, e2e)
docker/            # Docker Compose 설정
docs/              # Phase별 문서
.github/workflows/ # CI/CD (test, lint, claude-review, auto-fix)
```

## 코드 컨벤션

### Python (Backend + Data Collector)
- ruff로 포맷팅/린트 (커밋 전 필수)
- Pydantic v2 모델 사용 (BaseModel, BaseSettings)
- async/await 기반 (FastAPI, SQLAlchemy async)
- 테스트: pytest + pytest-asyncio

### TypeScript (Frontend)
- Next.js 14 App Router
- ESLint로 린트 (커밋 전 필수)
- `"use client"` 지시어 필요 시 명시

### 커밋 메시지
```
<type>(<scope>): <subject> (#이슈번호)
```
type: feat, fix, refactor, test, docs, chore

## 주의사항

### ruff 린터 대응
- ruff가 미사용 import를 자동 제거함
- import 추가와 사용처를 반드시 동시에 수정 (Write로 전체 파일 작성 권장)

### 디렉토리 이름
- `data-collector/` (하이픈) - 절대 `data_collector/`로 변경하지 않음
- CI 워크플로우에서 이 경로를 참조함

### 보안
- SECRET_KEY: 프로덕션에서 필수 환경변수 (DEBUG 모드에서만 기본값 허용)
- SSRF 방어: IP 차단 + 호스트네임 차단 + DNS rebinding 방어 (data-collector/schemas.py)
- 프롬프트 인젝션: 2-Layer 방어 (InputSanitizer + PromptIsolator, backend/shared/security.py)
- 타이밍 공격 방어: 존재하지 않는 사용자에도 bcrypt verify 실행

### CI 워크플로우 동기화
- main과 develop의 `.github/workflows/` 파일이 동일해야 claude-code-action 검증 통과
- claude-code-review.yml은 `claude_code_oauth_token` 사용 (API key 아님)

### .gitignore 주의
- `lib/` 패턴이 `frontend/lib/`도 차단함 → `!frontend/lib/` 예외 추가 필요
- `frontend/lib/` 파일은 `git add -f`로 강제 추가

## 테스트 실행

```bash
# Backend 전체
cd backend && python -m pytest ../tests/ -v --tb=short

# Data Collector
cd data-collector && python -m pytest tests/ -v --tb=short

# Frontend 빌드 검증
cd frontend && npm run build

# 린트
ruff format backend/ && ruff check backend/
cd frontend && npm run lint
```

## Phase별 문서

각 Phase 완료 시 `docs/phase-NN-xxx.md` 문서를 함께 작성한다.
문서에는 구현 범위, API 명세, 테스트 결과, 알려진 제한사항을 포함한다.

## 언어

- 코드: 영어 (변수명, 주석, 커밋 메시지)
- 문서/리뷰/사용자 소통: 한국어
