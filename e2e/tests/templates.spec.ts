import { test, expect } from '@playwright/test';
import { generateTestUser, registerUser, loginUser, authenticatedContext } from './helpers';

test.describe('템플릿 (Templates)', () => {
  test('템플릿 목록 페이지 렌더링', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    await authPage.goto('/templates');

    // 템플릿 목록 페이지 요소 확인
    await expect(authPage.locator('h1:has-text("템플릿"), h1:has-text("Templates")')).toBeVisible({ timeout: 10000 });

    // 템플릿 생성 버튼 확인
    await expect(authPage.locator('button:has-text("새 템플릿"), button:has-text("New Template"), button:has-text("Create")')).toBeVisible();

    await context.close();
  });

  test('템플릿 생성 (파이프라인에서 저장)', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    // 파이프라인 에디터로 이동
    await authPage.goto('/pipeline-editor');
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    // 노드 추가
    const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await authPage.waitForTimeout(1000);
    }

    // 템플릿으로 저장 버튼 클릭
    const saveAsTemplateButton = authPage.locator('button:has-text("템플릿으로"), button:has-text("Save as Template"), button:has-text("Template")');

    if (await saveAsTemplateButton.isVisible()) {
      await saveAsTemplateButton.click();

      // 템플릿 이름 입력 다이얼로그
      const templateNameInput = authPage.locator('input[name="name"], input[placeholder*="템플릿"], input[placeholder*="Template"]');
      await templateNameInput.fill('테스트 템플릿');

      // 설명 입력 (선택사항)
      const descriptionInput = authPage.locator('textarea[name="description"], textarea[placeholder*="설명"], textarea[placeholder*="Description"]');
      if (await descriptionInput.isVisible()) {
        await descriptionInput.fill('E2E 테스트용 템플릿');
      }

      // 저장 확인 버튼
      const confirmButton = authPage.locator('button:has-text("저장"), button:has-text("Save"), button[type="submit"]').last();
      await confirmButton.click();

      // 성공 메시지 확인
      await expect(authPage.locator('text=/템플릿.*저장|Template.*saved|Success/i')).toBeVisible({ timeout: 5000 });
    }

    await context.close();
  });

  test('템플릿 목록에서 템플릿 확인', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    // 먼저 템플릿 생성
    await authPage.goto('/pipeline-editor');
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await authPage.waitForTimeout(1000);
    }

    const saveAsTemplateButton = authPage.locator('button:has-text("템플릿으로"), button:has-text("Save as Template"), button:has-text("Template")');
    if (await saveAsTemplateButton.isVisible()) {
      await saveAsTemplateButton.click();
      const templateNameInput = authPage.locator('input[name="name"], input[placeholder*="템플릿"], input[placeholder*="Template"]');
      await templateNameInput.fill('목록 테스트 템플릿');
      const confirmButton = authPage.locator('button:has-text("저장"), button:has-text("Save"), button[type="submit"]').last();
      await confirmButton.click();
      await authPage.waitForSelector('text=/템플릿.*저장|Template.*saved|Success/i', { timeout: 5000 });
    }

    // 템플릿 목록 페이지로 이동
    await authPage.goto('/templates');

    // 생성한 템플릿이 목록에 표시되는지 확인
    await expect(authPage.locator('text=목록 테스트 템플릿')).toBeVisible({ timeout: 10000 });

    await context.close();
  });

  test('템플릿 상세 보기', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    // 템플릿 생성
    await authPage.goto('/pipeline-editor');
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await authPage.waitForTimeout(1000);
    }

    const saveAsTemplateButton = authPage.locator('button:has-text("템플릿으로"), button:has-text("Save as Template"), button:has-text("Template")');
    if (await saveAsTemplateButton.isVisible()) {
      await saveAsTemplateButton.click();
      const templateNameInput = authPage.locator('input[name="name"], input[placeholder*="템플릿"], input[placeholder*="Template"]');
      await templateNameInput.fill('상세보기 테스트');
      const descriptionInput = authPage.locator('textarea[name="description"], textarea[placeholder*="설명"], textarea[placeholder*="Description"]');
      if (await descriptionInput.isVisible()) {
        await descriptionInput.fill('상세 정보를 확인하는 템플릿');
      }
      const confirmButton = authPage.locator('button:has-text("저장"), button:has-text("Save"), button[type="submit"]').last();
      await confirmButton.click();
      await authPage.waitForSelector('text=/템플릿.*저장|Template.*saved|Success/i', { timeout: 5000 });
    }

    // 템플릿 목록 페이지로 이동
    await authPage.goto('/templates');
    await authPage.waitForSelector('text=상세보기 테스트', { timeout: 10000 });

    // 템플릿 클릭하여 상세 페이지로 이동
    await authPage.click('text=상세보기 테스트');

    // 상세 페이지 URL 확인
    await authPage.waitForURL(/\/templates\/[a-f0-9-]+/);

    // 템플릿 정보 확인
    await expect(authPage.locator('h1:has-text("상세보기 테스트"), h2:has-text("상세보기 테스트")')).toBeVisible();
    await expect(authPage.locator('text=상세 정보를 확인하는 템플릿')).toBeVisible();

    // 파이프라인 다이어그램 표시 확인 (React Flow)
    await expect(authPage.locator('.react-flow')).toBeVisible({ timeout: 5000 });

    await context.close();
  });

  test('템플릿 포크 (복제)', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    // 템플릿 생성
    await authPage.goto('/pipeline-editor');
    await authPage.waitForSelector('.react-flow', { timeout: 10000 });

    const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await authPage.waitForTimeout(1000);
    }

    const saveAsTemplateButton = authPage.locator('button:has-text("템플릿으로"), button:has-text("Save as Template"), button:has-text("Template")');
    if (await saveAsTemplateButton.isVisible()) {
      await saveAsTemplateButton.click();
      const templateNameInput = authPage.locator('input[name="name"], input[placeholder*="템플릿"], input[placeholder*="Template"]');
      await templateNameInput.fill('포크 테스트 원본');
      const confirmButton = authPage.locator('button:has-text("저장"), button:has-text("Save"), button[type="submit"]').last();
      await confirmButton.click();
      await authPage.waitForSelector('text=/템플릿.*저장|Template.*saved|Success/i', { timeout: 5000 });
    }

    // 템플릿 목록 페이지로 이동
    await authPage.goto('/templates');
    await authPage.waitForSelector('text=포크 테스트 원본', { timeout: 10000 });

    // 템플릿 클릭하여 상세 페이지로 이동
    await authPage.click('text=포크 테스트 원본');
    await authPage.waitForURL(/\/templates\/[a-f0-9-]+/);

    // 포크 버튼 클릭
    const forkButton = authPage.locator('button:has-text("포크"), button:has-text("Fork"), button:has-text("복제"), button:has-text("Clone")');
    await forkButton.click();

    // 포크 성공 후 처리 확인
    // 1) 새 템플릿 이름 입력 다이얼로그가 나타날 수 있음
    const newNameInput = authPage.locator('input[name="name"], input[placeholder*="템플릿"], input[placeholder*="Template"]');
    if (await newNameInput.isVisible({ timeout: 2000 })) {
      await newNameInput.fill('포크 테스트 복제본');
      const confirmForkButton = authPage.locator('button:has-text("확인"), button:has-text("OK"), button[type="submit"]').last();
      await confirmForkButton.click();
    }

    // 2) 파이프라인 에디터로 이동하거나 템플릿 목록으로 리다이렉트
    await authPage.waitForTimeout(2000);

    // 템플릿 목록으로 돌아가서 복제본 확인
    await authPage.goto('/templates');

    // 복제된 템플릿이 목록에 있는지 확인
    const forkedTemplate = authPage.locator('text=/포크.*복제|Fork|Clone/i');
    await expect(forkedTemplate.first()).toBeVisible({ timeout: 10000 });

    await context.close();
  });

  test('템플릿 검색', async ({ page, request, browser }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    // 인증된 컨텍스트로 페이지 열기
    const context = await authenticatedContext(browser, token);
    const authPage = await context.newPage();

    // 여러 템플릿 생성
    const templateNames = ['검색테스트A', '검색테스트B', '다른템플릿'];

    for (const name of templateNames) {
      await authPage.goto('/pipeline-editor');
      await authPage.waitForSelector('.react-flow', { timeout: 10000 });

      const addButton = authPage.locator('button:has-text("Add"), button:has-text("추가")').first();
      if (await addButton.isVisible()) {
        await addButton.click();
        await authPage.waitForTimeout(500);
      }

      const saveAsTemplateButton = authPage.locator('button:has-text("템플릿으로"), button:has-text("Save as Template"), button:has-text("Template")');
      if (await saveAsTemplateButton.isVisible()) {
        await saveAsTemplateButton.click();
        const templateNameInput = authPage.locator('input[name="name"], input[placeholder*="템플릿"], input[placeholder*="Template"]');
        await templateNameInput.fill(name);
        const confirmButton = authPage.locator('button:has-text("저장"), button:has-text("Save"), button[type="submit"]').last();
        await confirmButton.click();
        await authPage.waitForSelector('text=/템플릿.*저장|Template.*saved|Success/i', { timeout: 5000 });
      }
    }

    // 템플릿 목록 페이지로 이동
    await authPage.goto('/templates');

    // 검색 입력 필드 찾기
    const searchInput = authPage.locator('input[type="search"], input[placeholder*="검색"], input[placeholder*="Search"]');

    if (await searchInput.isVisible()) {
      // 검색어 입력
      await searchInput.fill('검색테스트');

      // 검색 결과 확인
      await expect(authPage.locator('text=검색테스트A')).toBeVisible({ timeout: 5000 });
      await expect(authPage.locator('text=검색테스트B')).toBeVisible({ timeout: 5000 });

      // 다른 템플릿은 표시되지 않아야 함
      await expect(authPage.locator('text=다른템플릿')).not.toBeVisible();
    }

    await context.close();
  });
});
