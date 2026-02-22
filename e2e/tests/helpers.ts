import { Browser, APIRequestContext } from '@playwright/test';

export interface TestUser {
  email: string;
  password: string;
  username: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface ConversationResponse {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/**
 * 테스트용 고유 사용자 생성
 */
export function generateTestUser(): TestUser {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 10000);
  return {
    email: `test-${timestamp}-${random}@example.com`,
    password: 'TestPassword123!',
    username: `testuser-${timestamp}-${random}`,
  };
}

/**
 * 회원가입 API 호출
 */
export async function registerUser(
  request: APIRequestContext,
  user: TestUser
): Promise<void> {
  const response = await request.post('http://localhost:8000/api/v1/auth/register', {
    data: {
      email: user.email,
      password: user.password,
      username: user.username,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`Registration failed: ${response.status()} - ${body}`);
  }
}

/**
 * 로그인 API 호출 및 JWT 토큰 반환
 */
export async function loginUser(
  request: APIRequestContext,
  user: Pick<TestUser, 'email' | 'password'>
): Promise<string> {
  const response = await request.post('http://localhost:8000/api/v1/auth/login', {
    form: {
      username: user.email,
      password: user.password,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`Login failed: ${response.status()} - ${body}`);
  }

  const data: AuthResponse = await response.json();
  return data.access_token;
}

/**
 * JWT 토큰으로 인증된 브라우저 컨텍스트 생성
 */
export async function authenticatedContext(browser: Browser, token: string) {
  const context = await browser.newContext({
    extraHTTPHeaders: {
      Authorization: `Bearer ${token}`,
    },
  });

  // 로컬스토리지에 토큰 저장 (프론트엔드가 사용하는 방식)
  await context.addInitScript((authToken) => {
    localStorage.setItem('auth_token', authToken);
  }, token);

  return context;
}

/**
 * 대화 생성 API 호출
 */
export async function createConversation(
  request: APIRequestContext,
  token: string,
  title: string
): Promise<ConversationResponse> {
  const response = await request.post('http://localhost:8000/api/v1/conversations', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      title,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`Conversation creation failed: ${response.status()} - ${body}`);
  }

  return await response.json();
}
