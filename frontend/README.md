# Frontend — Next.js 14 App Router

AgentForge 멀티 에이전트 플랫폼의 프론트엔드 애플리케이션입니다.

## 개요

실시간 채팅 UI와 React Flow 기반 파이프라인 에디터를 제공하는 Next.js 14 App Router 애플리케이션입니다. 다크 테마를 기본으로 제공하며, WebSocket을 통한 실시간 통신과 JWT 인증을 지원합니다.

## 페이지 구조

- **app/page.tsx**: 루트 페이지 (SplitView: 채팅 + 파이프라인 에디터 토글)
- **app/layout.tsx**: 루트 레이아웃 (lang="ko", Tailwind globals.css 적용)
- **app/(auth)/login/page.tsx**: 로그인 페이지
- **app/(auth)/register/page.tsx**: 회원가입 페이지
- **app/(main)/conversations/page.tsx**: 대화 목록
- **app/(main)/conversations/[id]/page.tsx**: 대화 상세 (채팅)
- **app/(main)/templates/page.tsx**: 템플릿 목록/검색
- **app/(main)/templates/[id]/page.tsx**: 템플릿 상세/포크
- **app/(main)/dashboard/page.tsx**: 사용자 대시보드 (사용량 차트, 비용 차트, 파이프라인 이력)

## 주요 컴포넌트

### 채팅 UI

- **ChatWindow.tsx**: WebSocket 기반 실시간 채팅
  - JWT 인증 (Bearer token)
  - 10+ 메시지 타입 처리 (clarification, designs_presented, critique_complete, plan_generated, pipeline_started, pipeline_result, pipeline_failed, agent_completed, security_warning, error)
  - 타이핑 인디케이터
  - 연결 상태 표시 (연결됨/재연결 중/연결 실패)
- **SplitView.tsx**: 리사이즈 가능한 분할 패널 (localStorage에 위치 저장)
- **MessageBubble.tsx**: 메시지 렌더링 (역할별 스타일, 타임스탬프)

### 파이프라인 에디터 (React Flow)

- **pipeline-editor/PipelineEditor.tsx**: React Flow 메인 에디터
  - 템플릿 관리 (저장/불러오기/포크/공유)
  - 실행 제어 (시작/중지/상태 모니터링)
  - MiniMap, Controls, Background
- **pipeline-editor/nodes/AgentNode.tsx**: 에이전트 노드
  - 역할별 색상 코딩 (intent_analyzer, design_generator, critique_agent, code_generator, qa_validator)
  - 상태 인디케이터 (idle/running/completed/failed)
  - LLM 모델 표시 (gpt-4o, gpt-4o-mini, claude-3-5-sonnet 등)
- **pipeline-editor/panels/PropertyPanel.tsx**: 노드 속성 편집
  - customPrompt, temperature, maxTokens 설정
- **pipeline-editor/panels/TemplateListPanel.tsx**: 템플릿 관리
  - 저장/불러오기/포크/공유 기능
- **pipeline-editor/panels/Toolbar.tsx**: 노드 추가/실행/저장/불러오기/초기화
- **pipeline-editor/components/ProgressIndicator.tsx**: 파이프라인 실행 진행률 표시 ("2/5 agents completed")

### 대시보드

- **dashboard/page.tsx**: 대시보드 메인 페이지
- **dashboard/components/UsageChart.tsx**: 일별 사용량 LineChart (recharts)
- **dashboard/components/CostChart.tsx**: 일별 비용 BarChart (recharts)
- **dashboard/components/PipelineHistory.tsx**: 파이프라인 실행 이력 테이블

### 커스텀 훅

- **pipeline-editor/hooks/useFlowState.ts**: React Flow 상태 관리
- **pipeline-editor/hooks/usePipelineExecution.ts**: 파이프라인 실행 제어
- **pipeline-editor/hooks/useTemplates.ts**: 템플릿 CRUD

### 유틸리티

- **pipeline-editor/utils/designToFlow.ts**: Design API 응답 → React Flow 구조 변환
- **pipeline-editor/utils/flowToDesign.ts**: React Flow 구조 → Design API 요청 변환
- **pipeline-editor/utils/nodeDefaults.ts**: 노드 기본값 정의

## WebSocket 연결 흐름

### WebSocket 클라이언트

**lib/websocket.ts**: WebSocketClient 클래스

- 지수 백오프 재연결 (초기 1초, 최대 30초)
- 자동 재연결 (최대 재시도 횟수 제한 없음)
- 이벤트 리스너 패턴 (onMessage, onOpen, onClose, onError)

### 연결 URL

```
ws://NEXT_PUBLIC_WS_URL/api/v1/ws/chat/{conversationId}?token={accessToken}
```

### 메시지 타입

| 타입 | 설명 |
|------|------|
| `clarification` | 명확화 요청 |
| `designs_presented` | 디자인 제시 |
| `critique_complete` | 비평 완료 |
| `plan_generated` | 플랜 생성 완료 |
| `pipeline_started` | 파이프라인 시작 |
| `pipeline_result` | 파이프라인 결과 |
| `pipeline_failed` | 파이프라인 실패 |
| `agent_completed` | 에이전트 완료 |
| `security_warning` | 보안 경고 |
| `error` | 오류 메시지 |

## 라이브러리

### lib/websocket.ts
WebSocket 클라이언트 유틸리티

- 자동 재연결 로직
- 이벤트 기반 메시지 처리

### lib/api.ts
REST API fetch wrapper

- JWT Bearer 토큰 자동 주입 (Authorization 헤더)
- 에러 핸들링
- JSON 응답 파싱

### lib/auth-context.tsx
인증 컨텍스트 (React Context)

- `AuthProvider`: 인증 상태 관리 (login, logout, register)
- `useAuth()`: 인증 상태 접근 훅 (user, isAuthenticated, loading)
- localStorage 기반 토큰 관리 (`agentforge_access_token`, `agentforge_refresh_token`)

### lib/auth.ts
인증 함수

- `register(email, password, display_name)`: 회원가입
- `login(email, password)`: 로그인 (accessToken, refreshToken 반환)
- `refresh(refreshToken)`: 토큰 갱신
- `getMe(accessToken)`: 사용자 정보 조회
- 토큰 localStorage 관리 (`agentforge_access_token`, `agentforge_refresh_token`)

## 환경변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | 백엔드 REST API URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | 백엔드 WebSocket URL |

`.env.local` 파일에 정의하거나 배포 환경에서 설정합니다.

## 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `next` | 14.2.15 | React 프레임워크 |
| `react` | 18.3.1 | UI 라이브러리 |
| `react-dom` | 18.3.1 | React DOM 렌더러 |
| `reactflow` | 11.11.4 | 파이프라인 에디터 |
| `recharts` | ^3.7.0 | 대시보드 차트 (LineChart, BarChart) |
| `tailwindcss` | 3.4.1 | CSS 프레임워크 |
| `typescript` | 5.x | 타입 체킹 |
| `eslint` | 8.x | 린팅 |
| `vitest` | (dev) | 단위 테스트 프레임워크 |
| `@testing-library/react` | (dev) | React 컴포넌트 테스트 |

## 실행 방법

### 개발 서버

```bash
npm install
npm run dev
```

개발 서버는 [http://localhost:3000](http://localhost:3000)에서 실행됩니다.

### 프로덕션 빌드

```bash
npm run build
npm start
```

### 단위 테스트

```bash
npm test           # vitest run (CI용)
npx vitest         # watch 모드 (개발용)
npx vitest --ui    # UI 모드
```

43개 단위 테스트: API 클라이언트, 인증 컨텍스트, 페이지 컴포넌트, 훅 등

### 린트

```bash
npm run lint
```

ESLint를 실행하여 코드 스타일을 검사합니다.

## 디렉토리 구조

```
frontend/
├── app/
│   ├── (auth)/                      # 인증 페이지
│   │   ├── login/page.tsx           # 로그인
│   │   └── register/page.tsx        # 회원가입
│   ├── (main)/                      # 메인 페이지 (인증 필요)
│   │   ├── conversations/           # 대화 목록/상세
│   │   ├── dashboard/               # 사용자 대시보드
│   │   │   ├── page.tsx             # 대시보드 메인
│   │   │   └── components/          # UsageChart, CostChart, PipelineHistory
│   │   └── templates/               # 템플릿 목록/상세/포크
│   ├── components/
│   │   ├── ChatWindow.tsx           # WebSocket 채팅
│   │   ├── MessageBubble.tsx        # 메시지 렌더링
│   │   ├── SplitView.tsx            # 분할 패널
│   │   └── pipeline-editor/
│   │       ├── PipelineEditor.tsx   # React Flow 에디터
│   │       ├── nodes/
│   │       │   └── AgentNode.tsx    # 에이전트 노드
│   │       ├── panels/
│   │       │   ├── PropertyPanel.tsx      # 속성 편집
│   │       │   ├── TemplateListPanel.tsx  # 템플릿 관리
│   │       │   └── Toolbar.tsx            # 도구 모음
│   │       ├── components/
│   │       │   └── ProgressIndicator.tsx  # 실행 진행률
│   │       ├── hooks/
│   │       │   ├── useFlowState.ts        # Flow 상태
│   │       │   ├── usePipelineExecution.ts # 실행 제어
│   │       │   └── useTemplates.ts        # 템플릿 CRUD
│   │       └── utils/
│   │           ├── designToFlow.ts        # Design → Flow
│   │           ├── flowToDesign.ts        # Flow → Design
│   │           └── nodeDefaults.ts        # 노드 기본값
│   ├── globals.css                  # Tailwind 전역 스타일
│   ├── layout.tsx                   # 루트 레이아웃
│   └── page.tsx                     # 루트 페이지
├── lib/
│   ├── websocket.ts                 # WebSocket 클라이언트
│   ├── api.ts                       # REST API wrapper
│   ├── auth.ts                      # 인증 함수
│   └── auth-context.tsx             # 인증 컨텍스트 (React Context)
├── public/                          # 정적 파일
├── vitest.config.ts                 # Vitest 테스트 설정
├── vitest.setup.ts                  # 테스트 셋업 (jest-dom)
├── .env.local                       # 환경변수 (git ignore)
├── next.config.js                   # Next.js 설정
├── tailwind.config.ts               # Tailwind 설정
├── tsconfig.json                    # TypeScript 설정
└── package.json                     # 의존성 정의
```

## 기술 스택

- **Next.js 14**: App Router 기반 React 프레임워크
- **React 18**: UI 라이브러리
- **TypeScript**: 정적 타입 체킹
- **Tailwind CSS**: 유틸리티 우선 CSS 프레임워크
- **React Flow**: 노드 기반 다이어그램 라이브러리
- **Recharts**: 차트 라이브러리 (대시보드)
- **Vitest + React Testing Library**: 단위 테스트 (43개)
- **WebSocket API**: 실시간 통신
