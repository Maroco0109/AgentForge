import { test, expect } from '@playwright/test';
import { generateTestUser, registerUser, loginUser } from './helpers';

test.describe('인증 (Authentication)', () => {
  test('회원가입 페이지 렌더링', async ({ page }) => {
    await page.goto('/register');

    // 회원가입 폼 요소 확인
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('성공적인 회원가입', async ({ page }) => {
    const user = generateTestUser();

    await page.goto('/register');

    // 폼 작성
    await page.fill('input[name="email"]', user.email);
    await page.fill('input[name="password"]', user.password);
    await page.fill('input[name="username"]', user.username);

    // 제출 버튼 클릭
    await page.click('button[type="submit"]');

    // 회원가입 성공 후 로그인 페이지로 리다이렉트 또는 성공 메시지 확인
    await page.waitForURL(/\/(login|conversations)/);
  });

  test('중복 이메일 가입 실패', async ({ page, request }) => {
    const user = generateTestUser();

    // API로 먼저 사용자 생성
    await registerUser(request, user);

    await page.goto('/register');

    // 동일한 이메일로 가입 시도
    await page.fill('input[name="email"]', user.email);
    await page.fill('input[name="password"]', user.password);
    await page.fill('input[name="username"]', user.username + '2');

    await page.click('button[type="submit"]');

    // 에러 메시지 확인
    await expect(page.locator('text=/already (exists|registered)|이미 존재/i')).toBeVisible({ timeout: 5000 });
  });

  test('로그인 성공 → 메인 페이지 리다이렉트', async ({ page, request }) => {
    const user = generateTestUser();

    // 사용자 등록
    await registerUser(request, user);

    await page.goto('/login');

    // 로그인 폼 작성
    await page.fill('input[name="email"]', user.email);
    await page.fill('input[name="password"]', user.password);

    await page.click('button[type="submit"]');

    // 대화 목록 페이지로 리다이렉트 확인
    await page.waitForURL(/\/conversations/);

    // 인증된 상태 확인 (로그아웃 버튼 또는 사용자 메뉴 존재)
    await expect(page.locator('button:has-text("로그아웃"), button:has-text("Logout")')).toBeVisible({ timeout: 5000 });
  });

  test('잘못된 비밀번호 로그인 실패', async ({ page, request }) => {
    const user = generateTestUser();

    // 사용자 등록
    await registerUser(request, user);

    await page.goto('/login');

    // 잘못된 비밀번호로 로그인 시도
    await page.fill('input[name="email"]', user.email);
    await page.fill('input[name="password"]', 'WrongPassword123!');

    await page.click('button[type="submit"]');

    // 에러 메시지 확인
    await expect(page.locator('text=/incorrect|invalid|잘못/i')).toBeVisible({ timeout: 5000 });
  });

  test('로그아웃', async ({ page, request }) => {
    const user = generateTestUser();

    // 사용자 등록 및 로그인
    await registerUser(request, user);
    const token = await loginUser(request, user);

    await page.goto('/conversations');

    // 로컬스토리지에 토큰 설정
    await page.evaluate((authToken) => {
      localStorage.setItem('access_token', authToken);
    }, token);

    await page.reload();

    // 로그아웃 버튼 클릭
    const logoutButton = page.locator('button:has-text("로그아웃"), button:has-text("Logout")');
    await logoutButton.click();

    // 로그인 페이지로 리다이렉트 확인
    await page.waitForURL(/\/login/);

    // 토큰이 삭제되었는지 확인
    const tokenAfterLogout = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(tokenAfterLogout).toBeNull();
  });
});
