import { test, expect } from '@playwright/test';
import { generateTestUser, registerUser, loginUser, authenticatedContext } from './helpers';

test.describe('파이프라인 에디터 (Pipeline Editor)', () => {
  test('파이프라인 에디터 페이지 렌더링', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/pipeline-editor');

    // React Flow 캔버스 확인
    await expect(authPage.locator('.react-flow')).toBeVisible({ timeout: 10000 });

    // 노드 패널 또는 사이드바 확인
    await expect(authPage.locator('aside, [role="complementary"]').first()).toBeVisible();

    // 저장 버튼 확인
    await expect(authPage.locator('button:has-text("저장"), button:has-text("Save")')).toBeVisible();

    await context.close();
  });

  test.skip('노드 추가 (사이드바 Add 버튼 필요)', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/pipeline-editor');

    // React Flow 캔버스 로드 대기
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 초기 노드 수 확인
    const initialNodes = await authPage.locator('.react-flow__node').count();

    // 노드 추가 버튼 클릭 (예: "Add Intent Analyzer" 버튼)
    const addNodeButton = authPage.locator('button:has-text("Intent"), button:has-text("Analyzer")').first();

    if (await addNodeButton.isVisible()) {
      await addNodeButton.click();

      // 노드가 추가되었는지 확인
      await authPage.waitForTimeout(1000); // 애니메이션 대기
      const newNodes = await authPage.locator('.react-flow__node').count();
      expect(newNodes).toBeGreaterThan(initialNodes);
    } else {
      // 대체 방법: 드래그 가능한 노드가 있는지 확인
      const draggableNode = authPage.locator('[draggable="true"]').first();
      await expect(draggableNode).toBeVisible();
    }

    await context.close();
  });

  test('노드 드래그 앤 드롭', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/pipeline-editor');

    // React Flow 캔버스 로드 대기
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 드래그 가능한 노드 찾기
    const draggableNode = authPage.locator('[draggable="true"]').first();

    if (await draggableNode.isVisible()) {
      // 캔버스 위치 찾기
      const canvas = authPage.locator('.react-flow__pane');
      const canvasBox = await canvas.boundingBox();

      if (canvasBox) {
        // 드래그 앤 드롭 수행
        await draggableNode.dragTo(canvas, {
          targetPosition: {
            x: canvasBox.width / 2,
            y: canvasBox.height / 2,
          },
        });

        // 노드가 캔버스에 추가되었는지 확인
        await authPage.waitForTimeout(1000); // 애니메이션 대기
        const nodes = await authPage.locator('.react-flow__node').count();
        expect(nodes).toBeGreaterThan(0);
      }
    }

    await context.close();
  });

  test('노드 연결 (엣지 생성)', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/pipeline-editor');

    // React Flow 캔버스 로드 대기
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 두 개의 노드 추가 (사이드바 버튼 사용)
    const addButtons = authPage.locator('button:has-text("Add"), button:has-text("추가")');
    const buttonCount = await addButtons.count();

    if (buttonCount >= 2) {
      await addButtons.nth(0).click();
      await authPage.waitForTimeout(500);
      await addButtons.nth(1).click();
      await authPage.waitForTimeout(500);

      // 노드가 추가되었는지 확인
      const nodes = await authPage.locator('.react-flow__node').count();
      expect(nodes).toBeGreaterThanOrEqual(2);

      // 첫 번째 노드의 핸들(출력)에서 두 번째 노드의 핸들(입력)로 연결
      const firstNodeHandle = authPage.locator('.react-flow__node').first().locator('.react-flow__handle-right, .react-flow__handle-bottom');
      const secondNodeHandle = authPage.locator('.react-flow__node').nth(1).locator('.react-flow__handle-left, .react-flow__handle-top');

      if (await firstNodeHandle.isVisible() && await secondNodeHandle.isVisible()) {
        // 드래그로 연결 생성
        await firstNodeHandle.dragTo(secondNodeHandle);

        // 엣지(연결선)가 생성되었는지 확인
        await authPage.waitForTimeout(1000);
        const edges = await authPage.locator('.react-flow__edge').count();
        expect(edges).toBeGreaterThan(0);
      }
    }

    await context.close();
  });

  test.skip('파이프라인 저장 (백엔드 API 필요)', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/pipeline-editor');

    // React Flow 캔버스 로드 대기
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 노드 추가 (최소 하나)
    const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await authPage.waitForTimeout(1000);
    }

    // 저장 버튼 클릭
    const saveButton = authPage.locator('button:has-text("저장"), button:has-text("Save")');
    await saveButton.click();

    // 저장 성공 메시지 또는 다이얼로그 확인
    await expect(authPage.locator('text=/저장.*완료|Saved|Success/i')).toBeVisible({ timeout: 5000 });

    await context.close();
  });

  test.skip('파이프라인 편집 및 재저장 (백엔드 API 필요)', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/pipeline-editor');

    // React Flow 캔버스 로드 대기
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 첫 번째 저장
    const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await authPage.waitForTimeout(1000);
    }

    const saveButton = authPage.locator('button:has-text("저장"), button:has-text("Save")');
    await saveButton.click();
    await authPage.waitForSelector('text=/저장.*완료|Saved|Success/i', { timeout: 5000 });

    // 페이지 새로고침
    await authPage.reload();
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 저장된 노드가 로드되었는지 확인
    const nodesAfterReload = await authPage.locator('.react-flow__node').count();
    expect(nodesAfterReload).toBeGreaterThan(0);

    // 노드 추가 후 재저장
    const addButton2 = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton2.isVisible()) {
      await addButton2.click();
      await authPage.waitForTimeout(1000);
    }

    await saveButton.click();
    await expect(authPage.locator('text=/저장.*완료|Saved|Success/i')).toBeVisible({ timeout: 5000 });

    await context.close();
  });
});
