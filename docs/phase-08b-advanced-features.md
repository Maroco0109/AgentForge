# Phase 8B: Advanced Pipeline Editor Features

## 개요

Phase 8A에서 구현한 React Flow 에디터를 확장하여 고급 파이프라인 기능을 추가합니다.

## 구현 범위

### 1. 확장 에이전트 설정

- **ExtendedAgentSpec**: AgentSpec을 상속하여 추가 설정 지원
  - `temperature` (0.0~2.0): LLM 창의성 조절
  - `max_tokens` (1~16384): 최대 출력 토큰
  - `retry_count` (0~10): 재시도 횟수
  - `custom_prompt`: 커스텀 시스템 프롬프트
  - `is_custom_role`: 사용자 정의 역할 여부
- **BaseAgentNode**: 확장 매개변수를 LLM 호출 시 적용
- Pydantic field_validator로 범위 검증

### 2. 커스텀 에이전트 역할

- **CustomAgentNode**: 사용자 정의 역할의 에이전트 노드
  - `custom_prompt`가 있으면 시스템 프롬프트로 사용
  - 없으면 역할 기반 기본 프롬프트 생성
- PropertyPanel에 Custom Role 토글 + 텍스트 입력 추가

### 3. 병렬 실행 (Fan-out/Fan-in)

- **LangGraph Send() API**: 하나의 노드에서 여러 노드로 병렬 분기
- **EdgeSpec**: 명시적 엣지 토폴로지 정의
  - `source`, `target`: 에이전트 이름
  - `condition`: 선택적 조건 (필드-연산자-값)
- **그래프 빌더 확장**:
  - `edges` 필드가 있으면 명시적 토폴로지로 빌드
  - `edges` 없으면 기존 순차 실행 유지 (하위 호환)
  - 같은 source에서 나가는 다중 엣지 → fan-out
  - 여러 노드가 같은 target에 연결 → fan-in (LangGraph 자동 병합)

### 4. 조건 분기

- **안전한 조건 파싱**: `field op value` 형식만 허용
  - 허용 연산자: `>`, `<`, `>=`, `<=`, `==`
  - 숫자 값만 비교 (코드 인젝션 방지)
  - `eval()`/`exec()` 미사용
- **조건 평가**: 파이프라인 상태 또는 마지막 에이전트 결과에서 필드 추출
- **ConditionalEdge**: 점선 + 주황색 스타일, 조건 라벨 배지

### 5. 템플릿 공유

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/templates/shared` | GET | 공개 템플릿 목록 (최대 50개) |
| `/templates/{id}/fork` | POST | 공개 템플릿 복제 |
| `/templates/{id}` | PUT | `is_public` 토글 (기존 업데이트에 추가) |

- Fork: 원본 불변, 새 템플릿 생성 (소유권 = 현재 사용자)
- 비공개 템플릿 fork 시도 → 404 (IDOR 방지)
- 사용자당 템플릿 제한 (50개) 적용

## API 변경사항

### 신규 엔드포인트

```
GET  /api/v1/templates/shared     → TemplateListResponse[]
POST /api/v1/templates/{id}/fork  → TemplateResponse (201)
```

### 스키마 변경

- `TemplateUpdate`: `is_public: bool | None` 추가
- `ExtendedAgentSpec`: `AgentSpec` 확장 (temperature, max_tokens 등)
- `EdgeSpec`: 엣지 토폴로지 정의
- `ExtendedDesignProposal`: `DesignProposal` 확장 (edges 필드)

## 프론트엔드 변경

### 노드 확장
- AgentNodeData에 확장 필드 추가 (customPrompt, temperature 등)
- 고급 설정이 있는 노드에 배지 표시

### PropertyPanel 확장
- Custom Role 토글 + 텍스트 입력
- Advanced Settings 접이식 섹션
  - Temperature 슬라이더 (0~2)
  - Max Tokens 입력 (1~16384)
  - Retry Count 입력 (0~10)
  - Custom System Prompt 텍스트영역

### 조건부 엣지
- ConditionalEdge 컴포넌트: 점선 + 주황색 + 조건 라벨
- edgeTypes 등록으로 ReactFlow에서 렌더링

### 템플릿 공유 UI
- TemplateListPanel에 탭 UI: "My Templates" / "Shared Templates"
- My Templates: Share/Unshare 토글 버튼
- Shared Templates: Fork 버튼
- useTemplates 훅: fetchSharedTemplates, forkTemplate, shareTemplate 추가

### 그래프 변환
- flowToDesign: 병렬 분기/조건부 엣지 감지 → edges 필드 포함
- designToFlow: edges 필드 있으면 2D 레이아웃, 조건부 엣지 타입 설정

## 파일 변경 요약

| 파일 | 작업 |
|------|------|
| `backend/pipeline/extended_models.py` | **신규** - 확장 모델 |
| `backend/pipeline/agents/base.py` | 수정 - 확장 매개변수 |
| `backend/pipeline/agents/custom.py` | **신규** - CustomAgentNode |
| `backend/pipeline/graph_builder.py` | 수정 - 병렬/조건부 그래프 |
| `backend/shared/schemas.py` | 수정 - is_public 추가 |
| `backend/gateway/routes/templates.py` | 수정 - shared/fork 엔드포인트 |
| `frontend/.../edges/ConditionalEdge.tsx` | **신규** - 조건부 엣지 |
| `frontend/.../nodes/AgentNode.tsx` | 수정 - 확장 필드 |
| `frontend/.../nodes/AgentNodeTypes.ts` | 수정 - edgeTypes |
| `frontend/.../panels/PropertyPanel.tsx` | 수정 - Advanced Settings |
| `frontend/.../panels/TemplateListPanel.tsx` | 수정 - 탭/fork/share |
| `frontend/.../hooks/useTemplates.ts` | 수정 - shared/fork API |
| `frontend/.../utils/flowToDesign.ts` | 수정 - 병렬/조건부 |
| `frontend/.../utils/designToFlow.ts` | 수정 - 2D 레이아웃 |
| `frontend/.../utils/nodeDefaults.ts` | 수정 - 확장 기본값 |
| `frontend/.../PipelineEditor.tsx` | 수정 - edgeTypes |
| `tests/unit/test_extended_models.py` | **신규** - 18 테스트 |
| `tests/unit/test_parallel_graph.py` | **신규** - 11 테스트 |
| `tests/unit/test_conditional_edges.py` | **신규** - 17 테스트 |
| `tests/unit/test_template_sharing.py` | **신규** - 13 테스트 |

## 테스트 결과

```
565 passed, 0 failed (전체 테스트 스위트)
Phase 8B 신규: 59 테스트 통과
```

## 보안 고려사항

- 조건 분기: `eval()`/`exec()` 미사용, 정규식 기반 안전 파싱
- 허용 연산자: `>`, `<`, `>=`, `<=`, `==` (숫자만)
- 템플릿 공유: 비공개 템플릿 fork 시 404 (IDOR 방지)
- 소유권 분리: fork 시 새 UUID + 현재 사용자 소유

## 알려진 제한사항

- 조건 분기는 숫자 비교만 지원 (문자열 비교 미지원)
- 병렬 실행 시 에이전트 간 상태 공유는 `agent_results` 리스트 기반
- 최대 20개 에이전트 제한 유지
