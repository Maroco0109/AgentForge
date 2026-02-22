# Phase 8A: React Flow Pipeline Editor + Split View

## 개요

React Flow 기반 시각적 파이프라인 에디터를 추가하여 사용자가 에이전트 파이프라인을 시각적으로 설계하고 실행할 수 있게 합니다.

## 구현 범위

### 백엔드
- **PipelineTemplate 모델**: 파이프라인 템플릿 저장을 위한 DB 모델 + Alembic 마이그레이션
- **Template CRUD API**: 생성/조회/수정/삭제 엔드포인트 (소유권 검증, 50개 한도)
- **execute-direct 엔드포인트**: 토론 엔진을 건너뛰고 에디터에서 직접 파이프라인 실행

### 프론트엔드
- **SplitView**: 리사이즈 가능한 분할 패널 (좌: 채팅, 우: 에디터)
- **PipelineEditor**: React Flow 래퍼 컴포넌트
- **AgentNode**: 커스텀 노드 (이름, 역할, 모델, 상태 표시)
- **Toolbar**: Add Node, Run, Save, Load, Clear 버튼
- **PropertyPanel**: 선택한 노드의 속성 편집 사이드바
- **TemplateListPanel**: 템플릿 저장/불러오기 모달
- **flowToDesign**: React Flow 그래프 → DesignProposal 변환 (위상 정렬)
- **designToFlow**: DesignProposal → React Flow 그래프 변환 (자동 레이아웃)
- **usePipelineExecution**: 실행 상태 추적 훅
- **useTemplates**: Template CRUD API 훅

## API 명세

### Template API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/templates` | 템플릿 생성 |
| `GET` | `/api/v1/templates` | 사용자 템플릿 목록 |
| `GET` | `/api/v1/templates/{id}` | 템플릿 상세 |
| `PUT` | `/api/v1/templates/{id}` | 템플릿 수정 |
| `DELETE` | `/api/v1/templates/{id}` | 템플릿 삭제 |

### Pipeline API (추가)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/pipelines/execute-direct` | 에디터에서 직접 실행 |

## 보안

- 템플릿 소유권 검증: `user_id == current_user.id` (IDOR 방지, 404 통일)
- 사용자당 최대 50개 템플릿 제한
- 직접 실행도 기존 `check_budget()` / `acquire_pipeline_lock()` / `record_cost()` 경로 동일

## 테스트 결과

- `test_templates.py`: Template CRUD + 소유권 검증 + 유효성 검증
- `test_direct_execute.py`: 직접 실행 + 비용 확인 + 기존 API와의 로직 공유 검증

## 알려진 제한사항

- React Flow v11 사용 (v12는 React 19 필요, 프로젝트는 React 18.3.1)
- 동시 편집 미지원 (last-write-wins + `updated_at`)
- 프론트엔드는 TypeScript 컴파일 + ESLint로 검증 (런타임 테스트 없음)

## 다음 단계 (Phase 8B)

- 병렬 실행 (LangGraph `Send()` fan-out/fan-in)
- 조건부 엣지 (필드-연산자-값 비교)
- 커스텀 에이전트 노드 (사용자 정의 프롬프트/설정)
- 템플릿 공유 (공개 템플릿 + 복제)
