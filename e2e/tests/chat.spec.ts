import { test, expect } from '@playwright/test';
import { generateTestUser, registerUser, loginUser, createConversation, authenticatedContext } from './helpers';

test.describe('채팅 (Chat)', () => {
  test('대화 목록 페이지 렌더링', async ({ page, request }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    await page.goto('/conversations');

    // 로컬스토리지에 토큰 설정
    await page.evaluate((authToken) => {
      localStorage.setItem('auth_token', authToken);
    }, token);

    await page.reload();

    // 대화 목록 페이지 요소 확인
    await expect(page.locator('h1:has-text("대화"), h1:has-text("Conversations")')).toBeVisible({ timeout: 5000 });

    // 새 대화 버튼 확인
    await expect(page.locator('button:has-text("새 대화"), button:has-text("New Conversation")')).toBeVisible();
  });

  test('새 대화 생성', async ({ page, request }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    await page.goto('/conversations');

    // 로컬스토리지에 토큰 설정
    await page.evaluate((authToken) => {
      localStorage.setItem('auth_token', authToken);
    }, token);

    await page.reload();

    // 새 대화 버튼 클릭
    await page.click('button:has-text("새 대화"), button:has-text("New Conversation")');

    // 대화 생성 후 채팅 페이지로 이동 확인
    await page.waitForURL(/\/chat\/[a-f0-9-]+/);

    // 메시지 입력 영역 확인
    await expect(page.locator('textarea, input[type="text"]').last()).toBeVisible();
    await expect(page.locator('button:has-text("전송"), button:has-text("Send"), button[type="submit"]')).toBeVisible();
  });

  test('메시지 입력 및 전송', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 대화 생성
    const conversation = await createConversation(request, token, 'Test Chat');

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto(`/chat/${conversation.id}`);

    // 메시지 입력
    const messageInput = authPage.locator('textarea, input[type="text"]').last();
    await messageInput.fill('안녕하세요, 테스트 메시지입니다.');

    // 전송 버튼 클릭
    const sendButton = authPage.locator('button:has-text("전송"), button:has-text("Send"), button[type="submit"]');
    await sendButton.click();

    // 전송된 메시지가 화면에 표시되는지 확인
    await expect(authPage.locator('text=안녕하세요, 테스트 메시지입니다.')).toBeVisible({ timeout: 10000 });

    // 입력 필드가 비워졌는지 확인
    await expect(messageInput).toHaveValue('');

    await context.close();
  });

  test('대화 목록에서 대화 선택', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 여러 대화 생성
    const conv1 = await createConversation(request, token, 'First Conversation');
    const conv2 = await createConversation(request, token, 'Second Conversation');

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/conversations');

    // 대화 목록이 로드될 때까지 대기
    await authPage.waitForSelector('text=First Conversation, text=Second Conversation', { timeout: 10000 });

    // 첫 번째 대화 클릭
    await authPage.click('text=First Conversation');

    // 대화 페이지로 이동 확인
    await authPage.waitForURL(new RegExp(`/chat/${conv1.id}`));

    // 대화 제목 확인
    await expect(authPage.locator('text=First Conversation')).toBeVisible();

    // 뒤로가기
    await authPage.goBack();
    await authPage.waitForURL(/\/conversations/);

    // 두 번째 대화 클릭
    await authPage.click('text=Second Conversation');

    // 대화 페이지로 이동 확인
    await authPage.waitForURL(new RegExp(`/chat/${conv2.id}`));

    // 대화 제목 확인
    await expect(authPage.locator('text=Second Conversation')).toBeVisible();

    await context.close();
  });

  test('WebSocket 연결 및 실시간 메시지 수신', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 대화 생성
    const conversation = await createConversation(request, token, 'WebSocket Test');

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto(`/chat/${conversation.id}`);

    // WebSocket 연결 대기 (네트워크 요청 확인)
    const wsPromise = authPage.waitForEvent('websocket', { timeout: 10000 });

    // 메시지 입력 및 전송
    const messageInput = authPage.locator('textarea, input[type="text"]').last();
    await messageInput.fill('WebSocket 테스트 메시지');

    const sendButton = authPage.locator('button:has-text("전송"), button:has-text("Send"), button[type="submit"]');
    await sendButton.click();

    // WebSocket 연결 확인
    const ws = await wsPromise;
    expect(ws.url()).toContain('/ws/chat/');

    // 응답 메시지 대기 (AI 응답 또는 에코)
    await authPage.waitForSelector('text=WebSocket 테스트 메시지', { timeout: 15000 });

    await context.close();
  });
});
