# Phase 4: Design Generator + Critique Agent (Discussion Engine)

## 개요

Phase 4는 Discussion Engine의 핵심 구성요소를 구현합니다:
- **Design Generator**: 구조화된 요구사항으로부터 2-3개의 파이프라인 설계안 생성
- **Critique Agent**: "악마의 대변인" 역할로 설계안의 약점/리스크 분석
- **Discussion State Machine**: 7단계 상태 전이 관리 (UNDERSTAND → PLAN)
- **Discussion Memory**: 합의사항, 미결사항, 사용자 선호도 추적
- **Discussion Engine**: 위 모든 컴포넌트를 통합하는 메인 오케스트레이터

## 아키텍처

```
사용자 입력
    │
    ▼
┌─────────────────────────────────┐
│     Discussion Engine            │
│  (engine.py - 오케스트레이터)      │
│                                  │
│  ┌───────────┐  ┌────────────┐  │
│  │  Security  │  │   State    │  │
│  │  Filter    │  │  Machine   │  │
│  └─────┬─────┘  └─────┬──────┘  │
│        ▼               ▼        │
│  ┌───────────┐  ┌────────────┐  │
│  │  Intent   │  │  Memory    │  │
│  │  Analyzer │  │  Manager   │  │
│  └─────┬─────┘  └────────────┘  │
│        ▼                        │
│  ┌───────────┐  ┌────────────┐  │
│  │  Design   │→ │  Critique  │  │
│  │ Generator │  │   Agent    │  │
│  └───────────┘  └────────────┘  │
└─────────────────────────────────┘
```

## Discussion State Machine

### 7단계 상태 흐름

```
UNDERSTAND → DESIGN → PRESENT → DEBATE ─┐
                        ↑                │
                        │  feedback_received
                        │                ▼
                     PRESENT ← REFINE
                        │
                   user_satisfied
                        ▼
                     CONFIRM → PLAN
```

### 상태 설명

| 상태 | 설명 | 다음 상태 |
|------|------|----------|
| `UNDERSTAND` | 사용자 입력 분석 (Intent Analyzer) | DESIGN |
| `DESIGN` | 파이프라인 설계안 생성 | PRESENT |
| `PRESENT` | 설계안을 사용자에게 제시 | DEBATE |
| `DEBATE` | 사용자 피드백 수집 + 비판 분석 | REFINE 또는 CONFIRM |
| `REFINE` | 피드백 반영하여 설계안 수정 | PRESENT (재순환) |
| `CONFIRM` | 최종 설계안 확정 | PLAN |
| `PLAN` | 구현 계획 생성 | (종료) |

### 전이 이벤트

| 이벤트 | 설명 |
|--------|------|
| `requirements_analyzed` | 의도 분석 완료 |
| `designs_generated` | 설계안 생성 완료 |
| `designs_presented` | 사용자에게 제시 완료 |
| `feedback_received` | 사용자 피드백 수신 |
| `user_satisfied` | 사용자 만족 신호 감지 |
| `refined_designs_ready` | 수정된 설계안 준비 |
| `user_confirmed` | 최종 확인 |
| `restart` | 모든 상태에서 UNDERSTAND로 복귀 |

### 라운드 제한

- 최대 5라운드 (설정 가능)
- `force_decision_mode()`: 최대 라운드 도달 시 `true` 반환
- 강제 결정 모드에서는 사용자에게 설계안 선택을 유도

## Design Generator

### 동작 방식

1. **LLM 기반 생성**: Multi-LLM 라우터를 통해 GPT-4o/Sonnet 급 모델로 설계안 생성
2. **폴백 생성**: LLM 미사용 시 패턴 기반 템플릿으로 3가지 설계안 자동 생성

### 설계안 구조 (`DesignProposal`)

```python
class DesignProposal(BaseModel):
    name: str                    # 설계안 이름
    description: str             # 설계안 설명
    agents: list[AgentSpec]      # 에이전트 목록
    pros: list[str]              # 장점
    cons: list[str]              # 단점
    estimated_cost: str          # 예상 비용
    complexity: str              # "low" | "medium" | "high"
    recommended: bool            # 추천 여부
```

### 폴백 설계안 템플릿

| 설계안 | 복잡도 | 에이전트 | 비용 |
|--------|:------:|---------|:----:|
| Simple Sequential Pipeline | low | collector → processor → formatter | ~$0.01-0.03 |
| Standard Pipeline with Validation | medium | collector → validator → analyzer → reporter | ~$0.05-0.10 |
| Advanced Multi-Agent Pipeline | high | collector → validator → analyzer → cross_checker → synthesizer → reporter | ~$0.15-0.30 |

### LLM 응답 파싱

- JSON 코드 블록 자동 추출 (```` ```json ... ``` ````)
- 파싱 실패 시 자동 폴백
- 빈 결과 시 폴백 호출

## Critique Agent

### 역할

"악마의 대변인"으로서 설계안의 약점과 리스크를 다각도로 분석합니다.

### 분석 관점 (6가지)

| 관점 | 설명 |
|------|------|
| Weaknesses | 구조적/논리적 약점 |
| Risks | 프로덕션 환경에서의 위험 요소 |
| Edge Cases | 처리되지 않는 예외 상황 |
| Security Concerns | 보안 취약점 |
| Cost Concerns | 비용 관련 우려사항 |
| Scalability Notes | 확장성 평가 |

### 결과 구조 (`CritiqueResult`)

```python
class CritiqueResult(BaseModel):
    design_name: str
    weaknesses: list[str]
    risks: list[str]
    edge_cases: list[str]
    security_concerns: list[str]
    cost_concerns: list[str]
    scalability_notes: list[str]
    overall_score: float          # 0.0 ~ 1.0
    recommendation: str
```

### 휴리스틱 폴백 규칙

| 조건 | 점수 변화 | 지적 내용 |
|------|:---------:|----------|
| 에이전트 수 < 2 | -0.10 | 에러 복구 옵션 부족 |
| 에이전트 수 > 5 | -0.05 | 조정 오버헤드 증가 |
| validator 역할 없음 | -0.10 | 데이터 검증 부재 |
| 고가 모델 3개 이상 사용 | 경고 | 비용 최적화 권고 |
| 복잡도 불일치 (over/under) | -0.15 | 과잉/과소 설계 |
| collector 존재 | 경고 | 외부 데이터 검증 필요 |
| critic/cross_checker 없음 | 경고 | 환각 미검증 |

## Discussion Memory

### 추적 항목

| 항목 | 용도 |
|------|------|
| `agreements` | 합의된 결정 사항 |
| `open_questions` | 미결 질문 |
| `user_preferences` | 사용자 선호도 (키-값) |
| `design_history` | 라운드별 설계안 스냅샷 |
| `critique_history` | 라운드별 비판 결과 |
| `round_summaries` | 라운드별 요약 |
| `resolved_questions` | 해결된 질문 (질문-해결 쌍) |

### LLM 컨텍스트 생성

`get_context_for_llm(max_chars=4000)`:
- 합의사항, 미결사항, 선호도, 최근 3라운드 요약 포함
- `max_chars` 제한으로 토큰 오버플로 방지
- 초과 시 잘림 표시 (`... (truncated)`)

## Discussion Engine

### 메시지 처리 흐름

```python
async def process_message(user_input: str) -> dict:
    # 1. 보안 검사 (sanitize_and_isolate)
    # 2. 현재 상태에 따라 라우팅
    # 3. 상태별 핸들러 실행
    # 4. 구조화된 응답 반환
```

### 보안

- **Layer 1**: `InputSanitizer` - 프롬프트 인젝션 패턴 탐지 (영어 + 한국어)
- **Layer 2**: `PromptIsolator` - XML 태그로 사용자 입력 격리

### 사용자 만족 신호 감지

| 언어 | 방식 | 키워드 |
|------|------|--------|
| 한국어 | substring 매칭 | 좋아, 괜찮, 확인, 선택, 결정, 이걸로, 이것으로, 승인, 동의 |
| 영어 | word-boundary regex | ok, good, confirm, select, choose |

영어는 `\b` word boundary를 사용하여 "not ok", "not good" 등의 오탐을 방지합니다.

### 응답 타입

| 타입 | 설명 |
|------|------|
| `security_warning` | 프롬프트 인젝션 감지 |
| `clarification` | 추가 정보 요청 |
| `designs_presented` | 설계안 제시 |
| `critique_complete` | 비판 분석 완료 |
| `plan_generated` | 실행 계획 생성 완료 |
| `error` | 오류 발생 |

### Confirm → Plan 흐름

`_handle_confirm`에서 설계안 선택 후:
1. `_selected_design`에 직접 저장 (agreement 문자열 검색 대신)
2. `_handle_plan()` 즉시 호출 (추가 사용자 입력 불필요)
3. 최종 응답에 `selected_design`, `discussion_summary` 포함

## 파일 구조

```
backend/discussion/
├── __init__.py
├── engine.py              # Discussion Engine 메인 오케스트레이터
├── intent_analyzer.py     # Intent Analyzer (Phase 3에서 구현)
├── design_generator.py    # Design Generator
├── critique_agent.py      # Critique Agent
├── state_machine.py       # Discussion State Machine
└── memory.py              # Discussion Memory

backend/shared/
└── security.py            # 프롬프트 인젝션 방어 (Phase 3에서 구현)
```

## 테스트

### 테스트 범위 (59개 테스트)

| 테스트 파일 | 테스트 수 | 대상 |
|------------|:---------:|------|
| `test_state_machine.py` | 15 | 상태 전이, 라운드 제한, 직렬화 |
| `test_design_generator.py` | 11 | 설계안 생성, LLM 파싱, 폴백 |
| `test_critique_agent.py` | 10 | 비판 분석, 점수 계산, 폴백 |
| `test_discussion_memory.py` | 10 | 메모리 CRUD, 컨텍스트 생성 |
| `test_discussion_engine.py` | 13 | 전체 흐름, 보안, 에러 처리 |

### 주요 테스트 시나리오

- 정상/비정상 상태 전이
- 라운드 제한 도달 시 강제 결정 모드
- LLM 응답 파싱 (정상/비정상 JSON)
- LLM 미사용 시 폴백 동작
- 프롬프트 인젝션 차단
- 만족 신호 감지 (한국어/영어, false positive 방지)
- Confirm → Plan 즉시 전이
- 전체 UNDERSTAND → PLAN 워크플로우

### 테스트 실행

```bash
cd /home/maroco/multi_agents-phase4
python -m pytest tests/ -v --tb=short -k "discussion or state_machine or design_generator or critique or memory"
```

## 의존성

### Phase 3 의존성
- `backend.discussion.intent_analyzer`: Intent Analyzer (Phase 3)
- `backend.pipeline.llm_router`: Multi-LLM 라우터 (Phase 3)
- `backend.shared.security`: 프롬프트 인젝션 방어 (Phase 3)

### Python 패키지
- `pydantic` (v2): 데이터 모델 정의 및 검증
- Phase 3 의존성 (litellm, 등)

## 알려진 제한사항

1. **LLM 미연결 시 폴백 전용**: LLM API 키가 설정되지 않으면 패턴 기반 템플릿만 사용
2. **토론 기록 비영속적**: 현재 인메모리 저장만 지원 (Phase 7에서 DB 저장 예정)
3. **단일 세션**: 다중 사용자 동시 토론은 Phase 7 통합 시 구현
4. **폴백 설계안 다양성 제한**: 3개 고정 템플릿 (LLM 사용 시에는 다양한 설계안 생성)

## 리뷰 수정 이력

### 1차 리뷰
- `isolated_input` 사용: `_handle_understand`에서 원본 대신 격리된 입력 사용
- Memory `max_chars` 제한: `get_context_for_llm(max_chars=4000)` 추가
- 상태 전이 실패 시 유효 이벤트 목록 반환

### 2차 리뷰
- 영어 만족 신호에 word-boundary regex 적용 (false positive 방지)
- `_handle_confirm` → `_handle_plan()` 즉시 호출 (UX 일관성)
- `_selected_design` 인스턴스 변수로 설계안 직접 참조 (fragile string search 제거)
