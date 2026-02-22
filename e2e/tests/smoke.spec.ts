import { test, expect } from '@playwright/test';

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000';

test.describe('Smoke Tests', () => {
  test('프론트엔드 루트 페이지 로딩', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);

    // Next.js 앱이 렌더링되었는지 확인
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('백엔드 헬스체크 응답', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/health`);
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('status');
  });
});
