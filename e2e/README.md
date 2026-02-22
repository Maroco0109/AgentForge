# AgentForge E2E Tests

Playwright를 사용한 AgentForge 프론트엔드 E2E 테스트 스위트입니다.

## 사전 요구사항

- Node.js 18+
- Docker Compose (백엔드 및 프론트엔드 서비스 실행용)
- 백엔드: http://localhost:8000
- 프론트엔드: http://localhost:3000

## 설치

```bash
cd e2e
npm install
npx playwright install chromium
```

## 테스트 실행

### 전체 테스트 실행 (헤드리스)

```bash
npm test
```

### UI 모드로 실행 (디버깅용)

```bash
npm run test:ui
```

### 브라우저 보이기 모드로 실행

```bash
npm run test:headed
```

### 특정 테스트 파일만 실행

```bash
npx playwright test tests/auth.spec.ts
```

### 특정 테스트만 실행

```bash
npx playwright test tests/auth.spec.ts -g "로그인 성공"
```

## 테스트 리포트

테스트 실행 후 HTML 리포트 보기:

```bash
npm run report
```

## 테스트 구조

```
e2e/
├── playwright.config.ts    # Playwright 설정
├── package.json            # 의존성 및 스크립트
├── tests/
│   ├── helpers.ts          # 공통 헬퍼 함수 (인증, 사용자 생성 등)
│   ├── auth.spec.ts        # 인증 관련 테스트
│   ├── chat.spec.ts        # 채팅 기능 테스트
│   ├── pipeline-editor.spec.ts  # 파이프라인 에디터 테스트
│   └── templates.spec.ts   # 템플릿 CRUD 테스트
└── README.md
```

## 테스트 범위

### auth.spec.ts
- 회원가입 페이지 렌더링
- 성공적인 회원가입
- 중복 이메일 가입 실패
- 로그인 성공 → 메인 페이지 리다이렉트
- 잘못된 비밀번호 로그인 실패
- 로그아웃

### chat.spec.ts
- 대화 목록 페이지 렌더링
- 새 대화 생성
- 메시지 입력 및 전송
- 대화 목록에서 대화 선택
- WebSocket 연결 및 실시간 메시지 수신

### pipeline-editor.spec.ts
- 파이프라인 에디터 페이지 렌더링
- 노드 추가 (버튼 클릭)
- 노드 드래그 앤 드롭
- 노드 연결 (엣지 생성)
- 파이프라인 저장
- 파이프라인 편집 및 재저장

### templates.spec.ts
- 템플릿 목록 페이지 렌더링
- 템플릿 생성 (파이프라인에서 저장)
- 템플릿 목록에서 템플릿 확인
- 템플릿 상세 보기
- 템플릿 포크 (복제)
- 템플릿 검색

## 헬퍼 함수

`tests/helpers.ts`에서 제공하는 주요 함수:

- `generateTestUser()`: 고유한 테스트 사용자 생성
- `registerUser(request, user)`: API를 통한 회원가입
- `loginUser(request, user)`: API를 통한 로그인 및 JWT 토큰 반환
- `authenticatedContext(browser, token)`: JWT 인증된 브라우저 컨텍스트 생성
- `createConversation(request, token, title)`: API를 통한 대화 생성

## CI/CD 통합

GitHub Actions에서 실행하려면:

```yaml
- name: Install dependencies
  run: |
    cd e2e
    npm install
    npx playwright install --with-deps chromium

- name: Run E2E tests
  run: |
    cd e2e
    npm test

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: e2e/playwright-report/
```

## 문제 해결

### 서비스가 준비되지 않은 경우

`playwright.config.ts`의 `webServer.timeout`을 늘려보세요:

```typescript
webServer: {
  timeout: 180000,  // 3분
}
```

### 테스트가 간헐적으로 실패하는 경우

타임아웃 값을 늘리거나 `waitForSelector` 타임아웃을 조정하세요:

```typescript
await page.waitForSelector('.element', { timeout: 10000 });
```

### Docker Compose가 시작되지 않는 경우

수동으로 서비스를 시작한 후 테스트:

```bash
cd docker
docker compose up -d
cd ../e2e
npm test
```

## 주의사항

- 각 테스트는 독립적이며 고유한 테스트 데이터를 생성합니다
- API 호출은 셋업용, UI 인터랙션은 검증용으로 사용합니다
- 테스트 실행 전 백엔드와 프론트엔드가 정상 작동해야 합니다
- CI 환경에서는 재시도 횟수가 2회로 설정됩니다
