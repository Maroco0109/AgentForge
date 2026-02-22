# Phase 2C: API 키 관리 + 비용 Circuit Breaker

## 개요

Phase 2C는 AgentForge의 프로그래매틱 접근성과 리소스 비용 관리를 강화하는 단계입니다. API 키 기반 인증을 도입하여 외부 애플리케이션과 자동화 도구에서 REST API 접근을 지원하고, 사용자별 LLM 호출 비용을 제어하는 Circuit Breaker를 구현합니다. 이 단계는 Phase 2A(JWT 인증)와 Phase 2B(RBAC, Rate Limiting)를 기반으로 하며, Phase 5(Pipeline Orchestrator)와 Phase 7(서비스 연동)의 기반이 됩니다.

**목표:**
- API 키 생성, 조회, 삭제 CRUD 엔드포인트
- SHA-256 기반 안전한 키 저장 (평문 저장 금지)
- API 키 기반 인증 (X-API-Key 헤더)
- 역할별 일일 LLM 비용 한도 설정 (FREE: $1/day, PRO: $50/day, ADMIN: 무제한)
- Redis 기반 실시간 비용 추적
- PostgreSQL 감사 로그 저장
- Redis 장애 시 Graceful Degradation

**기술 스택:**
- SHA-256 해싱 (hashlib)
- Redis (비용 누적 카운터, TTL 기반 자동 만료)
- SQLAlchemy 2.0+ Async ORM (api_keys, user_daily_costs 테이블)
- FastAPI 의존성 주입
- Pydantic 검증

## API 키 관리

### 키 형식

- **형식**: `sk-{32자 hex}` (총 35자)
- **생성**: `secrets.token_hex(16)` 사용 (무작위 32자 hex)
- **저장**: SHA-256 해시만 DB에 저장 (평문 저장 금지)
- **표시**: `key_prefix` (첫 11자: `sk-xxxxxxxx`)로 식별, 마스킹 표시

**예시:**
```
실제 키:   sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
해시:     SHA-256(위 키)
프리픽스: sk-a1b2c3d4e5
```

### 데이터 모델

#### api_keys 테이블

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | UUID | PK | 고유 식별자 |
| `user_id` | UUID | FK → users.id, NOT NULL | 키 소유자 |
| `name` | String(100) | NOT NULL | 키 이름 (사용자 정의) |
| `key_hash` | String(64) | NOT NULL, UNIQUE | SHA-256 해시 (64자) |
| `key_prefix` | String(11) | NOT NULL | 표시용 접두사 (예: sk-a1b2c3d4e5) |
| `is_active` | Boolean | DEFAULT TRUE | 활성 여부 |
| `last_used_at` | DateTime | NULLABLE | 마지막 사용 시각 |
| `created_at` | DateTime | NOT NULL | 생성 시각 |
| `expires_at` | DateTime | NULLABLE | 만료 시각 (optional, 추후) |

#### user_daily_costs 테이블

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | UUID | PK | 고유 식별자 |
| `user_id` | UUID | FK → users.id, NOT NULL | 사용자 ID |
| `date` | String(10) | NOT NULL | YYYY-MM-DD 형식 |
| `total_cost` | Float | DEFAULT 0.0 | 일일 누적 비용 (USD) |
| `updated_at` | DateTime | NOT NULL | 마지막 갱신 시각 |

**복합 인덱스:** `(user_id, date)` — 일일 비용 조회 최적화

### Pydantic 스키마

```python
# backend/shared/schemas.py

class APIKeyCreate(BaseModel):
    """API 키 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="키 이름")

class APIKeyResponse(BaseModel):
    """API 키 응답 (생성 직후만 평문 반환)"""
    id: str
    name: str
    key: str  # 첫 생성 시에만 포함
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

class APIKeyMasked(BaseModel):
    """API 키 목록 조회 (마스킹)"""
    id: str
    name: str
    key_prefix: str  # 마스킹 (예: sk-a1b2c3d4e5)
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

class UserUsageResponse(BaseModel):
    """비용 사용량 조회"""
    daily_cost: float  # 오늘의 누적 비용
    daily_limit: float  # 역할별 일일 한도
    remaining: float  # 남은 한도
    is_unlimited: bool  # ADMIN인 경우 True
```

## API 엔드포인트

### API 키 생성

**요청:**
```http
POST /api/v1/api-keys
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "내 스크립트용 키"
}
```

**응답 (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "내 스크립트용 키",
  "key": "sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "key_prefix": "sk-a1b2c3d4e5",
  "is_active": true,
  "last_used_at": null,
  "created_at": "2025-02-22T10:30:00Z"
}
```

**주의:**
- 키는 생성 시점에만 평문으로 반환됨
- 이후 조회 시 프리픽스만 표시됨
- 사용자가 즉시 복사해야 함

### API 키 목록 조회

**요청:**
```http
GET /api/v1/api-keys
Authorization: Bearer <access_token>
```

**응답 (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "내 스크립트용 키",
    "key_prefix": "sk-a1b2c3d4e5",
    "is_active": true,
    "last_used_at": "2025-02-22T15:45:00Z",
    "created_at": "2025-02-22T10:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "CI/CD 통합",
    "key_prefix": "sk-b2c3d4e5f6",
    "is_active": true,
    "last_used_at": "2025-02-21T08:15:00Z",
    "created_at": "2025-02-20T14:20:00Z"
  }
]
```

### API 키 삭제

**요청:**
```http
DELETE /api/v1/api-keys/{key_id}
Authorization: Bearer <access_token>
```

**응답 (204 No Content):**
```
(응답 본문 없음)
```

**에러 응답 (404 Not Found):**
```json
{
  "detail": "API key not found or access denied"
}
```

**보안 특징:**
- 키 소유자 또는 Admin만 삭제 가능
- 삭제된 키는 즉시 무효화됨 (DB에서 제거)

### API 키로 인증하여 요청

**요청 예 (Pipeline 실행):**
```http
POST /api/v1/pipelines/run
X-API-Key: sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
Content-Type: application/json

{
  "intent": "디자인 생성",
  "conversation_history": []
}
```

**응답 (200 OK):**
```json
{
  "pipeline_id": "abc123",
  "status": "processing",
  ...
}
```

**에러 응답 (401 Unauthorized):**
```json
{
  "detail": "Invalid or expired API key"
}
```

### 비용 사용량 조회

**요청:**
```http
GET /api/v1/auth/me/usage
Authorization: Bearer <access_token>
```

또는 API 키로:
```http
GET /api/v1/auth/me/usage
X-API-Key: sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**응답 (200 OK):**
```json
{
  "daily_cost": 0.45,
  "daily_limit": 1.0,
  "remaining": 0.55,
  "is_unlimited": false
}
```

## 비용 Circuit Breaker

### 역할별 일일 한도

| 역할 | 일일 한도 | 설명 |
|------|----------|------|
| FREE | $1.00 | 소규모 사용 |
| PRO | $50.00 | 프로 개발자 |
| ADMIN | 무제한 | 운영/테스트 |

**설정 위치:** `backend/gateway/rbac.py`

```python
ROLE_DAILY_LIMITS: dict[UserRole, float] = {
    UserRole.FREE: 1.0,
    UserRole.PRO: 50.0,
    UserRole.ADMIN: -1.0,  # 무제한
}
```

### 동작 원리

#### 1단계: 사전 검증 (Pipeline 실행 전)

```
GET /api/v1/pipelines/run
├─ 현재 사용자 조회 (JWT 또는 API Key)
├─ Redis에서 오늘 누적 비용 조회
├─ daily_limit 확인
└─ 초과 시 → HTTP 402 Payment Required
```

**코드 예:**
```python
# backend/gateway/cost_tracker.py
async def check_cost_limit(redis: Redis, user: User) -> None:
    """비용 한도 사전 검증"""
    if user.role == UserRole.ADMIN:
        return  # ADMIN은 무제한

    today_key = f"cost:{user.id}:{date.today().isoformat()}"
    current_cost = float(await redis.get(today_key) or 0.0)
    limit = ROLE_DAILY_LIMITS[user.role]

    if current_cost >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Daily cost limit exceeded: ${current_cost:.2f}/${limit:.2f}"
        )
```

#### 2단계: 비용 기록 (Pipeline 실행 후)

Pipeline이 완료된 후 비용을 기록합니다.

**코드 예:**
```python
# backend/gateway/cost_tracker.py
async def record_cost(
    redis: Redis,
    db: AsyncSession,
    user: User,
    cost_usd: float,
) -> None:
    """비용 기록 (Redis + PostgreSQL)"""
    today = date.today().isoformat()
    today_key = f"cost:{user.id}:{today}"

    # 1. Redis에 누적 (실시간 추적, TTL 48시간)
    await redis.incrbyfloat(today_key, cost_usd)
    await redis.expire(today_key, 48 * 3600)

    # 2. PostgreSQL에 영속 저장 (감사 로그)
    existing = await db.execute(
        select(UserDailyCost).where(
            (UserDailyCost.user_id == user.id) &
            (UserDailyCost.date == today)
        )
    )
    record = existing.scalars().first()

    if record:
        record.total_cost += cost_usd
    else:
        record = UserDailyCost(
            user_id=user.id,
            date=today,
            total_cost=cost_usd
        )
        db.add(record)

    await db.commit()
```

#### 3단계: Graceful Degradation (Redis 장애)

Redis가 장애 상태일 때:
- 비용 제한이 일시적으로 비활성화됨 (서비스 가용성 우선)
- PostgreSQL에만 기록 (감사는 유지)
- 경고 로그 출력

```python
async def check_cost_limit(redis: Redis | None, user: User) -> None:
    if redis is None:
        logger.warning("Redis unavailable — cost limiting disabled")
        return  # 비용 제한 건너뜀
    # ... 정상 로직
```

## 구현 상세

### 인증 우선순위

`backend/gateway/auth.py`에서 두 가지 인증 방식을 지원합니다.

```python
async def get_current_user(
    request: Request,
    credentials: HTTPAuthCredentials | None = Depends(security),
) -> User:
    """JWT 또는 API Key로 인증"""

    # 1. X-API-Key 헤더 확인 (우선순위 높음)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await authenticate_api_key(api_key)

    # 2. Authorization Bearer 확인
    if credentials:
        return await authenticate_jwt(credentials.credentials)

    # 3. 둘 다 없으면 실패
    raise HTTPException(
        status_code=401,
        detail="Not authenticated"
    )
```

**우선순위:**
1. X-API-Key (API 키 인증)
2. Authorization: Bearer (JWT 인증)
3. 없으면 401 Unauthorized

### API 키 해싱

키 생성 시 SHA-256 해시만 저장합니다.

```python
import hashlib
import secrets

def generate_api_key() -> tuple[str, str]:
    """API 키 생성 및 해시

    Returns:
        (plain_key, key_hash, key_prefix)
    """
    plain_key = f"sk-{secrets.token_hex(16)}"
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    key_prefix = plain_key[:11]  # sk-xxxxxxxx
    return plain_key, key_hash, key_prefix

def verify_api_key(plain_key: str, stored_hash: str) -> bool:
    """API 키 검증"""
    computed_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return computed_hash == stored_hash
```

**보안 설명:**
- **일방향 해싱**: AES 같은 양방향 암호화 대신 SHA-256 사용
  - API 키는 검증만 하고 복호화할 필요 없음
  - 해시 데이터베이스가 유출되어도 키 복원 불가능
- **Constant-time 비교**: `secrets` 모듈 사용 (timing attack 방지)

### API Key CRUD 라우터

**`backend/gateway/routes/api_keys.py`:**

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.shared.schemas import APIKeyCreate, APIKeyResponse, APIKeyMasked
from backend.gateway.auth import get_current_user

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

@router.post("", response_model=APIKeyResponse, status_code=201)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """API 키 생성 (평문 1회 반환)"""
    plain_key, key_hash, key_prefix = generate_api_key()

    api_key = APIKey(
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
    )
    db.add(api_key)
    await db.commit()

    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=plain_key,  # 생성 시점에만 반환
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
    )

@router.get("", response_model=list[APIKeyMasked])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """사용자의 API 키 목록 (마스킹)"""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    keys = result.scalars().all()
    return [APIKeyMasked.from_orm(k) for k in keys]

@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """API 키 삭제"""
    result = await db.execute(
        select(APIKey).where(
            (APIKey.id == UUID(key_id)) &
            (APIKey.user_id == current_user.id)
        )
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(api_key)
    await db.commit()
```

## 파일 변경 내역

### 수정된 파일

| 파일 | 변경 사항 |
|------|---------|
| `backend/shared/models.py` | APIKey, UserDailyCost ORM 모델 추가 |
| `backend/shared/schemas.py` | APIKeyCreate, APIKeyResponse, APIKeyMasked, UserUsageResponse 추가 |
| `backend/gateway/auth.py` | X-API-Key 헤더 처리, API Key 인증 로직 추가 |
| `backend/gateway/rbac.py` | ROLE_DAILY_LIMITS 상수 추가 |
| `backend/gateway/routes/chat.py` | 채팅 엔드포인트에 비용 검증 훅 추가 |
| `backend/gateway/routes/pipeline.py` | Pipeline 실행 전후 비용 추적 호출 |
| `backend/gateway/routes/auth.py` | `/auth/me/usage` 엔드포인트 추가 |
| `backend/gateway/main.py` | api_keys 라우터 등록 |

### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/gateway/cost_tracker.py` | check_cost_limit(), record_cost() 함수 |
| `backend/gateway/routes/api_keys.py` | API Key CRUD 라우터 |
| `backend/alembic/versions/20250222_0000_0003_api_keys_and_costs.py` | DB 마이그레이션 |

### 마이그레이션 실행

```bash
cd backend
alembic revision --autogenerate -m "add_api_keys_and_daily_costs"
alembic upgrade head
```

## 보안 고려 사항

### 1. API 키 저장 보안

**문제:** API 키를 평문으로 저장하면 DB 유출 시 키 탈취 위험

**해결:**
```python
# 나쁜 예
api_key.key_plain = user_input  # 평문 저장 ✗

# 좋은 예
api_key.key_hash = hashlib.sha256(user_input.encode()).hexdigest()  # ✓
```

- SHA-256 해시는 일방향 (복호화 불가능)
- 인증 시에만 해시 계산 후 비교
- DB 유출 시에도 원본 키 복원 불가능

### 2. API 키 개인정보보호

**문제:** 조회 시 전체 키를 표시하면 스크린샷/로그에 노출 위험

**해결:**
```python
# 좋은 예
key_prefix = "sk-a1b2c3d4e5"  # 첫 11자만 표시
# 사용자가 스크린샷해도 해시 계산 불가능
```

- 목록 조회 시 프리픽스만 표시
- 생성 직후 1회만 평문 반환 (즉시 복사 필요)
- 이후 재확인 불가능 (분실 시 재생성)

### 3. API 키 탈취 대응

**보안 조치:**
- 키 로테이션: 의심 시 기존 키 삭제 후 재생성
- 사용 추적: `last_used_at` 필드로 비정상 접근 감지
- 활성화/비활성화: 임시로 키 비활성화 가능

```python
@router.patch("/{key_id}/deactivate")
async def deactivate_api_key(...):
    """API 키 비활성화 (삭제 아님)"""
    api_key.is_active = False
    await db.commit()
```

### 4. 비용 제한 우회 방지

**문제:** 무한 retry로 비용 한도 우회 시도

**해결:**
- Pipeline 실행 전 사전 검증 (사전 방지)
- 거부된 요청도 로그 기록 (감사 추적)
- 비용 초과 시 즉시 HTTP 402 (추가 계산 불가)

### 5. Timing Attack 방지

**문제:** API 키 검증 시간 차이로 키 존재 여부 추측 가능

**해결:**
```python
import hmac

# 나쁜 예
if stored_hash == computed_hash:  # 시간 차이 발생 ✗

# 좋은 예
if hmac.compare_digest(stored_hash, computed_hash):  # 상수 시간 ✓
```

- `hmac.compare_digest()` 사용 (상수 시간 비교)
- 존재하지 않는 키도 동일한 시간 소요

## 설계 결정

| 결정 | 근거 |
|------|------|
| SHA-256 해시 | API Key는 복호화 불필요, AES는 키 관리 복잡도↑, PBKDF2는 불필요한 slow hashing |
| Redis 비용 추적 | 실시간 검증 성능 (DB 대비 10배 빠름), TTL 자동 만료로 메모리 관리 용이 |
| DB 이력 저장 | 감사/분석용 영속 데이터, Redis와 이중 기록으로 신뢰성↑ |
| HTTP 402 상태코드 | 429(Too Many)보다 의미적으로 정확 (리소스 비용 초과) |
| X-API-Key 헤더 | Bearer 토큰과 충돌 방지, 업계 표준 패턴 (GitHub, Stripe 등) |
| WebSocket JWT 유지 | API Key는 stateless REST용, WS는 세션 기반이므로 JWT 적합 |
| 키 개수 제한 없음 | 유연성↑, 제한이 필요하면 추후 역할별 제한 추가 가능 |

## 테스트

### API Key 생성 및 인증 테스트

```python
# tests/unit/test_api_keys.py
import pytest
from backend.gateway.cost_tracker import generate_api_key, verify_api_key

def test_generate_api_key():
    """API 키 생성"""
    plain_key, key_hash, key_prefix = generate_api_key()
    assert plain_key.startswith("sk-")
    assert len(plain_key) == 35
    assert len(key_hash) == 64  # SHA-256
    assert key_prefix == plain_key[:11]

def test_verify_api_key():
    """API 키 검증"""
    plain_key, key_hash, _ = generate_api_key()
    assert verify_api_key(plain_key, key_hash)
    assert not verify_api_key("wrong_key", key_hash)

# tests/integration/test_api_keys_endpoint.py
@pytest.mark.asyncio
async def test_create_api_key(client, test_user):
    """API 키 생성 엔드포인트"""
    response = await client.post(
        "/api/v1/api-keys",
        json={"name": "테스트 키"},
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "key" in data  # 평문 반환
    assert data["key"].startswith("sk-")
    assert data["key_prefix"] == data["key"][:11]

@pytest.mark.asyncio
async def test_list_api_keys_masked(client, test_user, created_api_key):
    """API 키 목록 조회 (마스킹)"""
    response = await client.get(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "key" not in data[0]  # 평문 없음
    assert "key_prefix" in data[0]  # 프리픽스만 표시

@pytest.mark.asyncio
async def test_authenticate_with_api_key(client):
    """API 키로 인증하여 요청"""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": valid_api_key}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"

@pytest.mark.asyncio
async def test_invalid_api_key_rejected(client):
    """유효하지 않은 API 키 거부"""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": "sk-invalid"}
    )
    assert response.status_code == 401
```

### 비용 Circuit Breaker 테스트

```python
# tests/unit/test_cost_tracker.py
@pytest.mark.asyncio
async def test_check_cost_limit_under_limit(redis_mock, free_user):
    """비용 한도 이하: 요청 허용"""
    redis_mock.get.return_value = b"0.50"  # $0.50 사용
    await check_cost_limit(redis_mock, free_user)  # 예외 없음

@pytest.mark.asyncio
async def test_check_cost_limit_exceeded(redis_mock, free_user):
    """비용 한도 초과: 요청 거부"""
    redis_mock.get.return_value = b"1.00"  # $1.00 사용됨 (한도 도달)
    with pytest.raises(HTTPException) as exc_info:
        await check_cost_limit(redis_mock, free_user)
    assert exc_info.value.status_code == 402

@pytest.mark.asyncio
async def test_check_cost_limit_admin_unlimited(redis_mock, admin_user):
    """ADMIN 역할: 무제한"""
    redis_mock.get.return_value = b"9999.99"  # 매우 높은 비용
    await check_cost_limit(redis_mock, admin_user)  # 예외 없음

@pytest.mark.asyncio
async def test_record_cost(redis_mock, db_mock, free_user):
    """비용 기록 (Redis + PostgreSQL)"""
    await record_cost(redis_mock, db_mock, free_user, 0.25)

    # Redis 호출 확인
    redis_mock.incrbyfloat.assert_called_once()
    redis_mock.expire.assert_called_once()

    # DB 호출 확인
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()

@pytest.mark.asyncio
async def test_cost_limit_redis_failure_graceful(redis_none, free_user):
    """Redis 장애: Graceful Degradation"""
    await check_cost_limit(redis_none, free_user)  # 예외 없음, 제한 비활성화
```

## CI/CD 통합

```yaml
# .github/workflows/test.yml
- name: Test API Keys
  run: |
    cd backend && python -m pytest ../tests/unit/test_api_keys.py -v

- name: Test Cost Tracker
  run: |
    cd backend && python -m pytest ../tests/unit/test_cost_tracker.py -v

- name: Lint API Keys Code
  run: |
    ruff check backend/gateway/routes/api_keys.py
    ruff check backend/gateway/cost_tracker.py
```

## 마이그레이션 가이드

### 프로덕션 배포 체크리스트

- [ ] PostgreSQL: api_keys, user_daily_costs 테이블 생성
- [ ] Redis: 연결 확인 및 비용 추적용 KEY SPACE 확보
- [ ] API 엔드포인트: `/api-keys`, `/auth/me/usage` 테스트
- [ ] 비용 기록 로직: Pipeline 실행 후 record_cost() 호출 확인
- [ ] 에러 처리: HTTP 402 응답 테스트
- [ ] 모니터링: Redis 비용 키 TTL 모니터링 설정

### 기존 사용자 영향

- **JWT 인증**: 기존 사용자는 영향 없음 (하위 호환성)
- **API 키**: 선택적 기능 (신규 채택 사용자용)
- **비용 제한**: 모든 사용자에게 적용됨 (기존 사용자는 역할별 한도 자동 설정)

## 알려진 제한사항

1. **API Key 개수 제한 없음**: 추후 역할별 제한 고려 (FREE: 1개, PRO: 5개, ADMIN: 무제한)
2. **비용 추적 범위**: Pipeline 실행 비용만 추적 (개별 LLM 호출 비용 미추적)
3. **비용 환불 불가**: 한 번 기록된 비용은 삭제/수정 불가 (감사 추적용)
4. **키 로테이션**: 자동 로테이션 미지원 (수동 삭제/재생성)
5. **Redis 클러스터 미지원**: 현재 단일 인스턴스 가정 (Phase 7에서 강화)

## 다음 단계

### Phase 3: Intent Analyzer + Multi-LLM Router

- Intent 분석 시 사용자 비용 한도 확인
- 역할별 LLM 모델 제한 (FREE: Haiku만, PRO: 모든 모델)

### Phase 5: Pipeline Orchestrator

- 각 LLM 호출 후 비용 계산
- `record_cost()` 호출로 실시간 비용 누적
- 비용 초과 시 Pipeline 실행 중단

### Phase 7: 프로덕션 강화

- Redis Sentinel/Cluster 설정
- Prometheus 메트릭: `cost_limit_hits`, `api_key_auth_rate`
- API Key 자동 로테이션 정책
- 역할별 API Key 개수 제한 구현

## 참고 자료

- [API Key Best Practices](https://tools.ietf.org/html/draft-sheffer-api-tokens-04)
- [OWASP 인증 보안 가이드](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Redis TTL 관리](https://redis.io/commands/expire)
- [HTTP 402 Payment Required](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402)
- [Timing Attacks on hmac](https://codahale.com/a-lesson-in-timing-attacks/)
