# Phase 2A: 인증 시스템 (JWT 기반)

## 개요

Phase 2A는 AgentForge의 보안 기반을 구축하는 단계입니다. PyJWT 기반의 JWT(JSON Web Token) 인증 체계를 도입하여 사용자 등록, 로그인, 토큰 관리를 제공합니다. 이 단계는 Phase 1의 인증 없는 상태를 개선하며, Phase 2B(RBAC, Rate Limiting)의 기반이 됩니다.

**목표:**
- PyJWT 기반 JWT 발급 및 검증 (access + refresh tokens)
- bcrypt 기반 안전한 비밀번호 해싱
- SECRET_KEY 환경 변수 검증 (프로덕션 필수)
- 사용자 등록/로그인/토큰 갱신 API 구현
- Alembic 비동기 마이그레이션 초기화
- 프론트엔드 TypeScript 인증 유틸리티

**기술 스택:**
- PyJWT (JWT 토큰 발급/검증)
- passlib + bcrypt (비밀번호 해싱)
- FastAPI 의존성 주입 (Depends)
- SQLAlchemy 2.0+ Async ORM
- Alembic (데이터베이스 마이그레이션)
- NextAuth.js v5 (프론트엔드, Phase 2B 계획)

## 데이터베이스 스키마

Phase 1에서 정의한 `users` 테이블을 확장합니다.

### 수정 사항

Users 테이블에 다음 필드 추가 필요:

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `password_updated_at` | TIMESTAMP | NOT NULL | 마지막 비밀번호 변경 시간 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 계정 활성화 상태 |
| `failed_login_attempts` | INTEGER | DEFAULT 0 | 연속 로그인 실패 횟수 (Phase 2B) |
| `locked_until` | TIMESTAMP | NULLABLE | 계정 잠금 시간 (Phase 2B) |

**Alembic 마이그레이션:**
```bash
alembic revision --autogenerate -m "add_auth_fields_to_users"
alembic upgrade head
```

## API 엔드포인트

### 사용자 등록

**요청:**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password_123",
  "display_name": "홍길동"
}
```

**응답 (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "홍길동",
  "role": "free",
  "created_at": "2024-02-21T10:30:00Z"
}
```

**검증 규칙:**
- 이메일: 유효한 이메일 형식
- 비밀번호: 최소 8자, 대문자, 소문자, 숫자 포함
- display_name: 2-100자, 한글/영문 혼합 허용
- 이메일 중복 검사: 기존 사용자 존재 시 400 Bad Request

### 사용자 로그인

**요청:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**응답 (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": "홍길동",
    "role": "free"
  }
}
```

**에러 응답 (401 Unauthorized):**
```json
{
  "detail": "Invalid email or password"
}
```

### 토큰 갱신

**요청:**
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}
```

**응답 (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 현재 사용자 조회

**요청:**
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**응답 (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "홍길동",
  "role": "free",
  "created_at": "2024-02-21T10:30:00Z"
}
```

**에러 응답 (401 Unauthorized):**
```json
{
  "detail": "Not authenticated"
}
```

## JWT 토큰 구조

### Access Token (15분 유효)

```
Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "role": "free",
  "exp": 1708417800,
  "iat": 1708417100,
  "type": "access"
}
```

### Refresh Token (7일 유효)

```
Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "exp": 1708956300,
  "iat": 1708350900,
  "type": "refresh"
}
```

## 설정 (Environment Variables)

**필수 환경 변수:**

```bash
# 보안 (프로덕션에서는 반드시 설정)
SECRET_KEY=your-very-long-random-secret-key-min-32-chars

# JWT 설정
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 기타
DEBUG=False  # 프로덕션에서는 False
```

**개발 환경 기본값:**
- `SECRET_KEY`: "dev-secret-key-change-in-production"
- `JWT_ALGORITHM`: "HS256"
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: 15
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: 7
- `DEBUG`: True

**경고:** 프로덕션 환경에서는 SECRET_KEY가 최소 32자 이상의 무작위 문자열이어야 하며, 환경 변수로만 설정되어야 합니다.

## 백엔드 구현

### 디렉토리 구조

```
backend/
├── shared/
│   ├── config.py         # Settings (JWT_* 변수 추가)
│   ├── models.py         # User 모델 확장
│   └── schemas.py        # Pydantic 스키마
├── auth/                 # Phase 2A 신규
│   ├── __init__.py
│   ├── routes.py         # Auth API 라우트
│   ├── schemas.py        # 요청/응답 스키마
│   ├── crud.py           # 사용자 CRUD 작업
│   ├── security.py       # 비밀번호 해싱, JWT 로직
│   └── dependencies.py   # FastAPI 의존성 (인증 확인)
└── gateway/
    └── main.py           # Auth 라우트 포함
```

### 핵심 모듈

**auth/security.py:**
```python
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, email: str) -> str:
    # JWT 발급 로직
    pass

def verify_token(token: str) -> dict:
    # JWT 검증 로직
    pass
```

**auth/dependencies.py:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    # Authorization 헤더에서 토큰 추출 및 검증
    pass
```

## 프론트엔드 구현

### TypeScript 인증 유틸리티

```typescript
// lib/auth.ts
export async function register(
  email: string,
  password: string,
  displayName: string
) {
  const response = await fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName })
  });
  return response.json();
}

export async function login(email: string, password: string) {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return response.json();
}

export function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token');
}
```

### API 호출 헬퍼

```typescript
// lib/api.ts
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
) {
  const token = getAccessToken();
  const headers = {
    ...options.headers,
    Authorization: `Bearer ${token}`
  };
  return fetch(url, { ...options, headers });
}
```

## 보안 고려 사항

### 현재 구현 (Phase 2A)

1. **비밀번호 해싱**: bcrypt를 사용한 강력한 해싱 (salting 자동)
2. **JWT 서명**: HS256 알고리즘으로 서명된 토큰
3. **토큰 유효기간**: Access Token (15분), Refresh Token (7일)
4. **CORS**: 프론트엔드 도메인만 허용
5. **HTTPS**: 프로덕션에서는 필수 (쿠키 설정 시)

### Phase 2B에서 추가할 사항

1. **Rate Limiting**: 로그인 시도 제한 (3회 실패 후 15분 잠금)
2. **RBAC**: 역할 기반 접근 제어
3. **Password Reset**: 이메일 기반 비밀번호 재설정
4. **토큰 블랙리스트**: 로그아웃 토큰 관리

### Phase 2C에서 추가할 사항

1. **API 키 관리**: 프로그래매틱 접근 인증
2. **비용 Circuit Breaker**: API 사용량 기반 차단

## 테스트

```python
# tests/unit/test_auth_security.py
import pytest
from backend.auth.security import hash_password, verify_password

def test_password_hashing():
    plain = "Test@Password123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)
    assert not verify_password("wrong_password", hashed)

# tests/integration/test_auth_endpoints.py
@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "Test@Password123",
            "display_name": "테스트"
        }
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login_success(client, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
```

## CI/CD 통합

GitHub Actions 워크플로우에 다음 추가:

```yaml
# .github/workflows/test.yml
- name: Test Auth Endpoints
  run: |
    docker-compose exec backend pytest tests/integration/test_auth_endpoints.py -v

- name: Lint Auth Code
  run: |
    docker-compose exec backend ruff check backend/auth/
```

## 마이그레이션 가이드

### 프로덕션 배포 체크리스트

- [ ] `SECRET_KEY` 환경 변수 설정 (최소 32자 무작위)
- [ ] `DEBUG=False` 설정
- [ ] HTTPS 활성화
- [ ] 데이터베이스 마이그레이션 실행
- [ ] JWT 토큰 유효기간 재검토
- [ ] Rate Limiting 설정 (Phase 2B)

## 알려진 제한 사항

1. **이메일 검증 없음**: 사용자 등록 시 이메일 확인 메일 미발송 (Phase 2B)
2. **Password Reset 없음**: 비밀번호 분실 시 복구 불가 (Phase 2B)
3. **토큰 블랙리스트 없음**: 로그아웃 후에도 토큰 유효 (Phase 2B)
4. **MFA 없음**: 2단계 인증 미지원 (향후 계획)

## 다음 단계

### Phase 2B: RBAC 및 Rate Limiting
- 역할별 권한 관리 (free, pro, admin)
- 로그인 실패 시 계정 잠금
- API 엔드포인트별 접근 제어
- WebSocket 연결 사용자 제한

### Phase 2C: API 키 및 Circuit Breaker
- 프로그래매틱 API 키 발급
- API 사용량 기반 차단
- 비용 제어 (LLM 호출 제한)

## 참고 자료

- [PyJWT 공식 문서](https://pyjwt.readthedocs.io/)
- [passlib 보안 가이드](https://passlib.readthedocs.io/)
- [FastAPI 보안](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT 베스트 프랙티스](https://tools.ietf.org/html/rfc8949)
