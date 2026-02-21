# Phase 5: Pipeline Orchestrator

## 개요

Phase 5는 LangGraph 기반 Pipeline Orchestrator를 구현합니다. Phase 4의 Discussion Engine에서 확정된 DesignProposal을 실행 가능한 LangGraph 파이프라인으로 변환하고 실행합니다.

**주요 특징:**
- LangGraph StateGraph 기반 에이전트 파이프라인 구성
- 5가지 에이전트 노드 타입 (Collector, Analyzer, Reporter, Validator, Synthesizer)
- 비용 및 토큰 추적
- 타임아웃 및 재시도 로직
- WebSocket 상태 업데이트 콜백

## 구현 범위

### 1. PipelineState (상태 관리)

**파일:** `/backend/pipeline/state.py`

LangGraph 호환 TypedDict로 파이프라인 실행 상태를 관리합니다.

```python
class PipelineState(TypedDict):
    """LangGraph pipeline state with reducer pattern for accumulating results."""

    design: dict                              # DesignProposal (dict)
    current_step: int                         # 현재 실행 단계 (0~50)
    max_steps: int                            # 최대 단계 수 (기본값: 50)
    timeout_seconds: int                      # 타임아웃 (기본값: 300초)
    agent_results: Annotated[list[dict], operator.add]  # 누적되는 에이전트 결과
    errors: Annotated[list[str], operator.add]          # 누적되는 에러 메시지
    status: str                               # "running" | "completed" | "failed" | "timeout"
    start_time: str                           # ISO 타임스탐프
    cost_total: float                         # 누적 비용 (USD)
    current_agent: str                        # 현재 실행 중인 에이전트
    output: str                               # 최종 출력
```

**특징:**
- Reducer pattern: `operator.add`를 사용하여 결과 자동 누적
- 각 에이전트 실행 후 상태 점진적 업데이트

### 2. AgentResult / PipelineResult (결과 모델)

**파일:** `/backend/pipeline/result.py`

```python
class AgentResult(BaseModel):
    """단일 에이전트 노드 실행 결과"""
    agent_name: str              # 에이전트 이름
    role: str                    # 역할 (collector, analyzer, reporter, etc.)
    content: str                 # 에이전트 출력 내용
    tokens_used: int             # 사용한 토큰 수
    cost_estimate: float         # 예상 비용 (USD)
    duration_seconds: float      # 실행 시간 (초)
    status: str                  # "success" | "failed"
    error: str | None            # 에러 메시지 (실패 시)


class PipelineResult(BaseModel):
    """파이프라인 전체 실행 결과"""
    design_name: str             # 디자인 이름
    status: str                  # "completed" | "failed" | "timeout"
    agent_results: list[AgentResult]  # 모든 에이전트 결과
    total_cost: float            # 전체 비용
    total_duration: float        # 전체 실행 시간
    total_tokens: int            # 전체 토큰 사용량
    output: str                  # 최종 출력 (reporter/synthesizer 우선)
    error: str | None            # 에러 요약
```

### 3. Agent Nodes (에이전트 구현)

**기본 클래스:** `/backend/pipeline/agents/base.py`

모든 에이전트는 `BaseAgentNode`를 상속합니다.

```python
class BaseAgentNode(ABC):
    """파이프라인 에이전트 노드의 추상 기본 클래스"""

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        llm_model: str = "gpt-4o-mini",
        router: LLMRouter | None = None,
    ):
        pass

    @abstractmethod
    def build_messages(self, state: PipelineState) -> list[dict]:
        """LLM 메시지 구성 (에이전트별 구현)"""
        pass

    def get_complexity(self) -> TaskComplexity:
        """모델 이름으로 작업 복잡도 자동 감지"""
        # mini/haiku → SIMPLE
        # opus → COMPLEX
        # 나머지 → STANDARD
        pass

    async def execute(self, state: PipelineState) -> PipelineState:
        """에이전트 실행 (3회 재시도 로직 포함)"""
        # 1. 메시지 구성
        # 2. LLM 호출
        # 3. AgentResult 생성
        # 4. 상태 업데이트 반환
        pass
```

**실행 흐름:**
1. `execute()` 호출 (LangGraph에서 자동)
2. `build_messages()` 호출로 LLM 메시지 구성
3. `llm_router.generate()` 호출
4. 성공 시 AgentResult 반환
5. 실패 시 최대 3회 재시도 (MAX_RETRIES=3)
6. 모든 재시도 실패 시 error 상태로 반환

#### 3.1 CollectorNode (데이터 수집)

**파일:** `/backend/pipeline/agents/collector.py`

데이터 수집 계획 수립. Phase 7에서 실제 Data Collector 통합될 때까지 모의 구현.

#### 3.2 AnalyzerNode (데이터 분석)

**파일:** `/backend/pipeline/agents/analyzer.py`

LLM 기반 데이터 분석. Critic/CrossChecker 역할도 재사용.

#### 3.3 ReporterNode (보고서 생성)

**파일:** `/backend/pipeline/agents/reporter.py`

파이프라인 결과를 최종 Markdown 보고서로 컴파일.

#### 3.4 ValidatorNode (데이터 검증)

**파일:** `/backend/pipeline/agents/validator.py`

데이터 품질 및 완전성 검증.

#### 3.5 SynthesizerNode (종합 분석)

**파일:** `/backend/pipeline/agents/synthesizer.py`

여러 분석 에이전트의 발견사항을 통합.

### 4. PipelineGraphBuilder (그래프 구성)

**파일:** `/backend/pipeline/graph_builder.py`

DesignProposal을 LangGraph StateGraph로 변환합니다.

**역할 → 노드 매핑 (ROLE_NODE_MAP):**

| 역할 | 노드 클래스 |
|------|-----------|
| collector | CollectorNode |
| analyzer | AnalyzerNode |
| reporter | ReporterNode |
| validator | ValidatorNode |
| synthesizer | SynthesizerNode |
| critic | AnalyzerNode (재사용) |
| cross_checker | AnalyzerNode (재사용) |
| (미지정) | AnalyzerNode (기본값) |

**조건 엣지 (_should_continue):**
- 에러 ≥ 3개 → END
- current_step ≥ max_steps → END
- status in (failed, timeout, completed) → END
- 그외 → continue (다음 노드)

### 5. PipelineOrchestrator (실행 엔진)

**파일:** `/backend/pipeline/orchestrator.py`

DesignProposal을 실행하는 메인 엔진입니다.

**타임아웃 구현:**
```python
final_state = await asyncio.wait_for(
    self._run_graph(compiled_graph, initial_state, on_status),
    timeout=timeout,  # 기본값: 300초 (5분)
)
```

**상태 업데이트 콜백 (on_status):**

```python
# 파이프라인 시작
await on_status({
    "type": "pipeline_started",
    "design_name": "...",
    "agent_count": 5,
})

# 에이전트 완료
await on_status({
    "type": "agent_completed",
    "agent_name": "analyzer_1",
    "status": "success",
    "duration": 2.34,
})

# 파이프라인 실패
await on_status({
    "type": "pipeline_failed",
    "reason": "timeout",
})
```

**출력 선택 로직:**
1. reporter/synthesizer 역할의 마지막 성공 출력 우선
2. 없으면 마지막 성공 에이전트 출력
3. 없으면 빈 문자열

### 6. LLM Router (모델 라우팅)

**파일:** `/backend/pipeline/llm_router.py`

작업 복잡도에 따라 최적의 LLM 모델을 선택합니다.

**작업 복잡도 레벨:**

| 복잡도 | 모델 (OpenAI) | 모델 (Anthropic) |
|------|-------------|-----------------|
| SIMPLE | gpt-4o-mini | claude-haiku-4-5-20251001 |
| STANDARD | gpt-4o | claude-sonnet-4-5-20250929 |
| COMPLEX | gpt-4o | claude-opus-4-6 |

**복잡도 자동 감지:**
- 에이전트 모델 이름으로 감지:
  - "mini" 또는 "haiku" → SIMPLE
  - "opus" → COMPLEX
  - 나머지 → STANDARD

### 7. Pipeline API Routes (API 엔드포인트)

**파일:** `/backend/gateway/routes/pipeline.py`

HTTP API로 파이프라인 실행을 제어합니다.

#### POST /api/v1/pipelines/execute

파이프라인 실행 시작 (동기 실행).

**응답:**
```json
{
  "pipeline_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "design_name": "data_analysis_pipeline",
  "started_at": "2025-02-22T10:30:00Z",
  "result": {
    "design_name": "data_analysis_pipeline",
    "status": "completed",
    "agent_results": [...],
    "total_cost": 0.003167,
    "total_duration": 4.68,
    "total_tokens": 1650,
    "output": "Final analysis report...",
    "error": null
  }
}
```

#### GET /api/v1/pipelines/{pipeline_id}/status

파이프라인 실행 상태 조회.

#### GET /api/v1/pipelines/{pipeline_id}/result

파이프라인 결과 조회 (상세).

### 8. Gateway Integration

**파일:** `/backend/gateway/main.py`

Pipeline router를 메인 FastAPI 앱에 등록합니다.

## 파일 구조

### 새로운 파일

```
backend/pipeline/
├── __init__.py
├── state.py                    # PipelineState (TypedDict)
├── result.py                   # AgentResult, PipelineResult
├── llm_router.py               # Multi-LLM Router (복잡도별 모델 선택)
├── orchestrator.py             # PipelineOrchestrator (메인 엔진)
├── graph_builder.py            # PipelineGraphBuilder
└── agents/
    ├── __init__.py
    ├── base.py                 # BaseAgentNode (추상 클래스)
    ├── collector.py            # CollectorNode
    ├── analyzer.py             # AnalyzerNode
    ├── reporter.py             # ReporterNode
    ├── validator.py            # ValidatorNode
    └── synthesizer.py          # SynthesizerNode

backend/gateway/routes/
├── pipeline.py                 # Pipeline API 엔드포인트

tests/unit/
├── test_pipeline_state.py      # 상태 관리 테스트
├── test_agent_nodes.py         # 에이전트 노드 테스트
├── test_graph_builder.py       # 그래프 빌더 테스트
├── test_pipeline_orchestrator.py  # Orchestrator 테스트
└── test_pipeline_routes.py     # API 라우트 테스트
```

### 수정된 파일

```
backend/gateway/main.py         # Pipeline router 등록
```

## 의존성

```toml
[tool.poetry.dependencies]
langgraph = ">=0.4.5"           # LangGraph 상태 머신
langchain-core = ">=0.2.27"     # 기본 구성요소
typing-extensions = ">=4.12.0"  # TypedDict, Annotated
openai = ">=1.3.0"              # OpenAI API
anthropic = ">=0.28.0"          # Anthropic Claude API
```

## 테스트 (34/34 통과)

### test_pipeline_state.py (6 tests)
- `test_pipeline_state_creation`: 상태 생성
- `test_agent_results_accumulation`: 결과 누적
- `test_errors_accumulation`: 에러 누적
- `test_state_status_transitions`: 상태 전이
- `test_cost_accumulation`: 비용 누적
- `test_step_counter`: 단계 카운터

### test_agent_nodes.py (13 tests)
- `test_get_complexity_*`: 복잡도 감지 (4 tests)
- `test_execute_success`: 성공 실행
- `test_execute_retry_on_failure`: 재시도 로직
- `test_execute_all_retries_exhausted`: 재시도 실패
- `test_build_messages` (Collector, Analyzer, Reporter, Validator, Synthesizer): 메시지 구성

### test_graph_builder.py (7 tests)
- `test_build_simple_graph`: 간단한 그래프
- `test_build_empty_agents_raises`: 에이전트 없음 (에러)
- `test_build_single_agent`: 단일 에이전트
- `test_build_with_all_roles`: 모든 역할
- `test_role_node_map_coverage`: 역할 매핑 커버리지
- `test_build_handles_duplicate_names`: 중복 이름 처리
- `test_unknown_role_defaults_to_analyzer`: 미지정 역할 기본값

### test_pipeline_orchestrator.py (5 tests)
- `test_execute_empty_design`: 빈 디자인 (에러)
- `test_execute_success`: 성공 실행
- `test_execute_with_status_callback`: 상태 콜백
- `test_execute_timeout`: 타임아웃
- `test_execute_graph_exception`: 그래프 예외

### test_pipeline_routes.py (3 tests)
- `test_execute_pipeline`: 파이프라인 실행
- `test_get_nonexistent_pipeline_status`: 없는 파이프라인 상태 조회
- `test_get_nonexistent_pipeline_result`: 없는 파이프라인 결과 조회

**테스트 실행:**
```bash
cd /home/maroco/multi_agents
python -m pytest tests/unit/test_pipeline_*.py tests/unit/test_agent_*.py tests/unit/test_graph_*.py -v
```

## 실행 흐름 (예제)

### 1. DesignProposal 생성 (Phase 4에서)

```python
design = DesignProposal(
    name="quarterly_sales_analysis",
    description="분기별 판매 데이터 분석",
    agents=[
        AgentSpec(
            name="data_collector",
            role="collector",
            description="판매 데이터 수집",
            llm_model="gpt-4o-mini",
        ),
        AgentSpec(
            name="sales_analyzer",
            role="analyzer",
            description="판매 추세 분석",
            llm_model="gpt-4o",
        ),
        AgentSpec(
            name="report_generator",
            role="reporter",
            description="분석 보고서 생성",
            llm_model="gpt-4o",
        ),
    ],
)
```

### 2. Orchestrator 실행

```python
orchestrator = PipelineOrchestrator()

async def status_callback(event: dict):
    """WebSocket으로 상태 전달"""
    print(f"Pipeline event: {event}")

result = await orchestrator.execute(
    design=design,
    on_status=status_callback,
    max_steps=50,
    timeout=300,
)
```

### 3. 실행 내부 동작

1. **Graph Builder:** DesignProposal → LangGraph StateGraph
   ```
   START → CollectorNode → AnalyzerNode → ReporterNode → END
   ```

2. **Initial State 설정:**
   ```python
   {
       "design": { /* 디자인 정보 */ },
       "current_step": 0,
       "max_steps": 50,
       "timeout_seconds": 300,
       "agent_results": [],
       "errors": [],
       "status": "running",
       "cost_total": 0.0,
       ...
   }
   ```

3. **Graph 실행 (astream):**
   - START 실행
   - CollectorNode 실행 → 상태 업데이트
   - AnalyzerNode 실행 → 상태 업데이트
   - ReporterNode 실행 → 상태 업데이트
   - END 도달

4. **상태 누적:**
   ```
   agent_results = [collector_result] + [analyzer_result] + [reporter_result]
   cost_total = 0.001 + 0.002 + 0.003 = 0.006
   ```

5. **최종 결과:**
   ```python
   PipelineResult(
       design_name="quarterly_sales_analysis",
       status="completed",
       agent_results=[...],
       total_cost=0.006,
       total_duration=6.78,
       total_tokens=2500,
       output="최종 보고서...",
   )
   ```

## 아키텍처 다이어그램

```
DesignProposal (Phase 4)
        ↓
PipelineGraphBuilder
        ↓
LangGraph StateGraph (compiled)
        ↓
PipelineOrchestrator.execute()
    ├── START → CollectorNode → AnalyzerNode → ReporterNode → END
    ├── Conditional edges: error/timeout → END
    ├── on_status callback → WebSocket
    └── PipelineResult (aggregated)
```

## 알려진 제한사항

### 1. CollectorNode 모의 구현
- 실제 Data Collector 마이크로서비스와 통합 없음
- Phase 7에서 REST API 호출로 변경 예정

### 2. 동기 실행
- 파이프라인 실행이 HTTP 요청을 차단함
- Phase 7에서 백그라운드 태스크 큐 추가 예정
- 대형 파이프라인 실행 시 타임아웃 주의

### 3. 메모리 저장소
- 파이프라인 실행 결과가 메모리에만 저장 (`_pipeline_runs` dict)
- 서버 재시작 시 데이터 손실
- Phase 7에서 PostgreSQL 저장소 추가

### 4. WebSocket 통합 없음
- `on_status` 콜백 구조는 WebSocket 준비 완료
- Phase 7에서 실제 WebSocket 메시지 전송

### 5. 에러 처리
- 일부 에러는 자동 재시도 (BaseAgentNode에서 3회)
- 전체 파이프라인 레벨 에러 핸들링 제한적
- Phase 7에서 상세 에러 추적 및 복구 로직 추가

## 성능 고려사항

### 타임아웃 설정
기본값: 300초 (5분)

```python
# 빠른 파이프라인 (2-3개 에이전트)
await orchestrator.execute(design, timeout=120)

# 중간 규모 (5-10개)
await orchestrator.execute(design, timeout=300)

# 복잡한 파이프라인 (10개 이상)
await orchestrator.execute(design, timeout=600)
```

### 비용 최적화
1. **작업 복잡도 맞추기:**
   ```python
   # 간단한 작업 → SIMPLE 모델 (저비용)
   AgentSpec(..., llm_model="gpt-4o-mini")

   # 복잡한 작업 → COMPLEX 모델 (고정확)
   AgentSpec(..., llm_model="gpt-4o")
   ```

2. **max_tokens 조정:**
   - BaseAgentNode.execute()에서 기본값: 4096
   - 필요에 따라 감소 (비용 절감)

## 다음 단계 (Phase 7)

1. **Data Collector 통합:**
   - CollectorNode → HTTP REST API 호출
   - 실제 데이터 수집 구현

2. **백그라운드 실행:**
   - 동기 → 비동기 변경
   - 태스크 큐 (Celery) 추가
   - 장시간 파이프라인 지원

3. **WebSocket 통합:**
   - 실시간 상태 업데이트
   - 프론트엔드 진행률 표시

4. **데이터베이스 저장:**
   - Pipeline runs 테이블 추가
   - 과거 실행 결과 조회 가능

5. **고급 기능:**
   - 파이프라인 재시도 및 부분 재개
   - 에이전트별 캐싱
   - 비용 회로 차단기 (Phase 2C와 통합)

## 코드 예제

### 기본 사용법

```python
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.discussion.design_generator import DesignProposal, AgentSpec

# 파이프라인 디자인 생성
design = DesignProposal(
    name="customer_analysis",
    description="고객 데이터 분석",
    agents=[
        AgentSpec(
            name="collector",
            role="collector",
            description="데이터 수집",
            llm_model="gpt-4o-mini",
        ),
        AgentSpec(
            name="analyzer",
            role="analyzer",
            description="패턴 분석",
            llm_model="gpt-4o",
        ),
        AgentSpec(
            name="reporter",
            role="reporter",
            description="결과 보고",
            llm_model="gpt-4o",
        ),
    ],
)

# Orchestrator 생성 및 실행
orchestrator = PipelineOrchestrator()
result = await orchestrator.execute(design)

# 결과 확인
print(f"Status: {result.status}")
print(f"Total cost: ${result.total_cost:.6f}")
print(f"Total duration: {result.total_duration}s")
print(f"Output:\n{result.output}")
```

### API 호출 예제

```bash
# 파이프라인 실행
curl -X POST http://localhost:8000/api/v1/pipelines/execute \
  -H "Content-Type: application/json" \
  -d '{
    "design": {
      "name": "test_pipeline",
      "agents": [...]
    }
  }'
```

## 요약

Phase 5는 LangGraph 기반 Pipeline Orchestrator를 통해 Design Proposal을 실행 가능한 멀티 에이전트 워크플로우로 변환합니다.

**핵심 특징:**
- 5가지 에이전트 타입으로 다양한 작업 지원
- 자동 복잡도 감지 기반 LLM 모델 라우팅
- 비용 및 토큰 실시간 추적
- 3회 자동 재시도 및 타임아웃 강제
- 상태 콜백으로 WebSocket 연동 준비

**완성도:**
- 구현: 100% (34/34 테스트 통과)
- 모의 구현: CollectorNode (Phase 7에서 실제 구현)
- 준비됨: WebSocket, 데이터베이스, 백그라운드 작업 (Phase 7)
