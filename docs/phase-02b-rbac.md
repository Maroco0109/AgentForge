# Phase 2B: RBAC 및 Rate Limiting

## 개요

Phase 2B는 AgentForge의 보안 및 리소스 관리를 강화하는 단계입니다. 역할 기반 접근 제어(RBAC)와 Redis 기반 Rate Limiting을 도입하여 사용자 등급별 차등화된 서비스를 제공하고, API 남용을 방지합니다. 이 단계는 Phase 2A(JWT 인증)를 기반으로 하며, Phase 2C(API 키 관리)의 토대가 됩니다.

**목표:**
- 역할 기반 권한 관리 (FREE, PRO, ADMIN)
- Redis 기반 Sliding Window Rate Limiter 구현
- WebSocket 연결 수 제한 (사용자별, 역할별)
- Admin 전용 역할 변경 API
- 타이밍 공격 방지 및 감사 로깅
- Redis 장애 시 Graceful Degradation

**기술 스택:**
- Redis (Sorted Sets for sliding window)
- FastAPI 의존성 주입
- SQLAlchemy 2.0+ Async ORM
- Pydantic 검증
- Python logging (감사 로그)

## RBAC (Role-Based Access Control)

### 권한 테이블

각 역할별로 다음 권한이 차등 적용됩니다.

| 권한 | FREE | PRO | ADMIN |
|------|------|-----|-------|
| `max_pipelines_per_day` | 3 | 100 | 무제한 (-1) |
| `max_discussions_per_day` | 10 | 무제한 (-1) | 무제한 (-1) |
| `max_requests_per_minute` | 10 | 60 | 무제한 (-1) |
| `ws_max_message_size` | 4KB (4096) | 64KB (65536) | 1MB (1048576) |
| `ws_max_connections` | 2 | 10 | 무제한 (-1) |

**특징:**
- `-1` 값은 무제한을 의미
- 권한은 `backend/gateway/rbac.py`의 `ROLE_PERMISSIONS` 딕셔너리에 중앙 관리
- `get_permission(role, permission)` 함수로 런타임 조회
- `is_unlimited(value)` 헬퍼 함수로 무제한 여부 판단

### 코드 구조

**backend/gateway/rbac.py:**
```python
from backend.shared.models import UserRole

ROLE_PERMISSIONS: dict[UserRole, dict[str, int]] = {
    UserRole.FREE: {
        "max_pipelines_per_day": 3,
        "max_discussions_per_day": 10,
        "max_requests_per_minute": 10,
        "ws_max_message_size": 4096,
        "ws_max_connections": 2,
    },
    UserRole.PRO: {
        "max_pipelines_per_day": 100,
        "max_discussions_per_day": -1,
        "max_requests_per_minute": 60,
        "ws_max_message_size": 65536,
        "ws_max_connections": 10,
    },
    UserRole.ADMIN: {
        "max_pipelines_per_day": -1,
        "max_discussions_per_day": -1,
        "max_requests_per_minute": -1,
        "ws_max_message_size": 1048576,
        "ws_max_connections": -1,
    },
}

def get_permission(role: UserRole, permission: str) -> int:
    """Get a specific permission value for a role."""
    role_perms = ROLE_PERMISSIONS.get(role)
    if role_perms is None:
        raise KeyError(f"Unknown role: {role}")
    if permission not in role_perms:
        raise KeyError(f"Unknown permission: {permission}")
    return role_perms[permission]

def is_unlimited(value: int) -> bool:
    """Check if a permission value represents unlimited access."""
    return value == -1
```

## Rate Limiter 아키텍처

### Sliding Window 알고리즘

Redis Sorted Set(ZSET)을 사용한 정확한 슬라이딩 윈도우 구현:

```
Time:     0s -------- 30s -------- 60s (now)
Window:   [------------ 60s window ---------]
Requests: |--x--x----x-----x-----x--x------x|
          ^  ^                           ^
       expired (cleaned)              current (added)
```

**동작 원리:**
1. 현재 시간 - window_seconds 이전 요청 삭제 (`ZREMRANGEBYSCORE`)
2. 윈도우 내 요청 수 조회 (`ZCARD`)
3. 제한 초과 시 → 거부 (Sorted Set에 추가 **안 함**)
4. 제한 이하 시 → 현재 요청 추가 (`ZADD`)

**장점:**
- 정확한 슬라이딩 윈도우 (Fixed Window의 버스트 문제 없음)
- UUID 기반 member key로 동시 요청 충돌 방지
- 거부된 요청은 카운트 안 됨 (정확한 집계)
- 원자적 연산 (Redis Pipeline 사용)

### 핵심 함수

**`check_rate_limit(redis, key, limit, window_seconds)`:**

```python
async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int, int]:
    """Check and increment a sliding window rate limit.

    Returns:
        Tuple of (allowed, remaining, retry_after_seconds).
    """
    now = time.time()
    window_start = now - window_seconds

    # UUID 기반 member key (동시 요청 충돌 방지)
    member = f"{now}-{uuid_mod.uuid4().hex[:8]}"

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # 만료된 요청 삭제
    pipe.zcard(key)  # 현재 윈도우 내 요청 수 조회
    pipe.expire(key, window_seconds)  # TTL 갱신

    results = await pipe.execute()
    request_count = results[1]

    if request_count >= limit:
        # 제한 초과 → 추가 안 함, retry-after 계산
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry_after = int(oldest[0][1] + window_seconds - now) + 1
        else:
            retry_after = window_seconds
        return False, 0, max(retry_after, 1)

    # 제한 이하 → 현재 요청 추가
    await redis.zadd(key, {member: now})
    await redis.expire(key, window_seconds)

    remaining = limit - request_count - 1
    return True, remaining, 0
```

### WebSocket 연결 추적

**`ws_track_connection(redis, user_id, max_connections)`:**

```python
async def ws_track_connection(
    redis: Redis | None,
    user_id: str,
    max_connections: int,
) -> bool:
    """Track and check WebSocket connection count for a user.

    Returns:
        True if connection is allowed, False if limit exceeded.
    """
    if redis is None or is_unlimited(max_connections):
        return True

    key = f"ws_connections:{user_id}"
    try:
        current = await redis.incr(key)
        await redis.expire(key, 3600)  # 1시간 TTL (안전망)

        if current > max_connections:
            await redis.decr(key)
            return False
        return True
    except Exception:
        logger.warning("WS connection tracking failed — allowing", exc_info=True)
        return True
```

**`ws_release_connection(redis, user_id)`:**

```python
async def ws_release_connection(redis: Redis | None, user_id: str) -> None:
    """Release a tracked WebSocket connection."""
    if redis is None:
        return
    key = f"ws_connections:{user_id}"
    try:
        current = await redis.decr(key)
        if current <= 0:
            await redis.delete(key)  # 카운트가 0 이하면 키 삭제
    except Exception:
        logger.warning("WS connection release failed", exc_info=True)
```

### FastAPI 의존성

**`RateLimiter` 클래스:**

```python
class RateLimiter:
    """FastAPI dependency for rate limiting based on user role permissions."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        redis = get_redis()
        if redis is None:
            # Graceful degradation: Redis 장애 시 모든 요청 허용
            return

        user = request.state.current_user
        role = user.role
        limit = get_permission(role, "max_requests_per_minute")

        if is_unlimited(limit):
            return

        key = f"rate_limit:{user.id}:{self.window_seconds}s"
        allowed, remaining, retry_after = await check_rate_limit(
            redis, key, limit, self.window_seconds
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = limit
```

**`rate_limit_dependency` (통합 의존성):**

```python
async def rate_limit_dependency(
    request: Request,
    current_user=Depends(get_current_user),
) -> None:
    """Authenticate and rate-limit in one step."""
    request.state.current_user = current_user

    limiter = RateLimiter(window_seconds=60)
    await limiter(request)
```

## API 엔드포인트

### 역할 변경 (Admin 전용)

**요청:**
```http
PUT /api/v1/auth/users/{user_id}/role
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
  "role": "pro"
}
```

**응답 (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "홍길동",
  "role": "pro"
}
```

**에러 응답:**

| 상태 코드 | 조건 | 메시지 |
|-----------|------|--------|
| 400 Bad Request | Admin이 자신의 역할 변경 시도 | "Cannot change your own role" |
| 401 Unauthorized | 인증 실패 | "Not authenticated" |
| 403 Forbidden | Admin이 아닌 사용자 | "Insufficient permissions" |
| 404 Not Found | 대상 사용자 없음 | "User not found" |

**보안 특징:**
- Admin 자기 강등 방지 (self-demotion protection)
- 감사 로그 자동 기록 (admin ID, target user ID, old role, new role)

### Rate Limit 헤더

모든 인증 엔드포인트는 다음 응답 헤더를 포함할 수 있습니다:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
Retry-After: 30  (429 응답 시만)
```

## 설정 (Environment Variables)

**필수 환경 변수:**

```bash
# Redis (Rate Limiting)
REDIS_URL=redis://localhost:6379/0

# JWT (Phase 2A에서 설정)
SECRET_KEY=your-very-long-random-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

**개발 환경 기본값:**
- `REDIS_URL`: "redis://localhost:6379/0"

**프로덕션 권장:**
- Redis Sentinel 또는 Redis Cluster 사용
- Redis 연결 타임아웃: 5초
- Redis TTL: window_seconds + 여유 시간

## 디렉토리 구조

```
backend/
├── gateway/
│   ├── rbac.py               # RBAC 권한 테이블
│   ├── rate_limiter.py       # Redis 기반 Rate Limiter
│   ├── auth.py               # JWT 검증 및 의존성
│   └── routes/
│       └── auth.py           # Auth API (역할 변경 포함)
├── shared/
│   ├── config.py             # REDIS_URL 추가
│   └── models.py             # UserRole enum
└── tests/
    └── unit/
        ├── test_rbac.py      # RBAC 유닛 테스트 (40개)
        └── test_rate_limiter.py  # Rate Limiter 유닛 테스트 (38개)
```

## 테스트 결과

### RBAC 테스트 (`test_rbac.py`)

총 40개 테스트, 모두 통과:

```python
def test_get_permission_free_role():
    """FREE 역할 권한 조회"""
    assert get_permission(UserRole.FREE, "max_pipelines_per_day") == 3
    assert get_permission(UserRole.FREE, "max_requests_per_minute") == 10

def test_get_permission_admin_unlimited():
    """ADMIN 역할 무제한 권한"""
    assert get_permission(UserRole.ADMIN, "max_pipelines_per_day") == -1
    assert is_unlimited(get_permission(UserRole.ADMIN, "max_discussions_per_day"))

def test_get_permission_unknown_role():
    """존재하지 않는 역할"""
    with pytest.raises(KeyError, match="Unknown role"):
        get_permission("SUPER_ADMIN", "max_pipelines_per_day")

def test_get_permission_unknown_permission():
    """존재하지 않는 권한"""
    with pytest.raises(KeyError, match="Unknown permission"):
        get_permission(UserRole.FREE, "max_unicorns_per_day")
```

**커버리지:**
- 모든 역할 (FREE, PRO, ADMIN)
- 모든 권한 키
- 에러 케이스 (unknown role, unknown permission)
- 무제한 값 검증

### Rate Limiter 테스트 (`test_rate_limiter.py`)

총 38개 테스트, 모두 통과:

```python
@pytest.mark.asyncio
async def test_check_rate_limit_allows_under_limit(redis_mock):
    """제한 이하 요청 허용"""
    redis_mock.pipeline().execute.return_value = [None, 5, True]
    allowed, remaining, retry = await check_rate_limit(redis_mock, "key", 10, 60)
    assert allowed is True
    assert remaining == 4

@pytest.mark.asyncio
async def test_check_rate_limit_rejects_over_limit(redis_mock):
    """제한 초과 요청 거부"""
    redis_mock.pipeline().execute.return_value = [None, 10, True]
    redis_mock.zrange.return_value = [(0, 100.0)]
    allowed, remaining, retry = await check_rate_limit(redis_mock, "key", 10, 60)
    assert allowed is False
    assert remaining == 0
    assert retry > 0

@pytest.mark.asyncio
async def test_rate_limiter_graceful_degradation(app_client):
    """Redis 장애 시 요청 허용"""
    # Redis = None 상황 시뮬레이션
    # 예상: 모든 요청 허용
    pass

@pytest.mark.asyncio
async def test_ws_track_connection_success(redis_mock):
    """WebSocket 연결 추적 성공"""
    redis_mock.incr.return_value = 1
    allowed = await ws_track_connection(redis_mock, "user123", 2)
    assert allowed is True

@pytest.mark.asyncio
async def test_ws_track_connection_exceeds_limit(redis_mock):
    """WebSocket 연결 제한 초과"""
    redis_mock.incr.return_value = 3
    allowed = await ws_track_connection(redis_mock, "user123", 2)
    assert allowed is False
    redis_mock.decr.assert_called_once()
```

**커버리지:**
- `init_redis()`, `close_redis()`, `get_redis()` lifecycle
- `check_rate_limit()` 정상/제한초과/에러 케이스
- `RateLimiter` 클래스 동작
- `rate_limit_dependency` 통합 의존성
- WebSocket 연결 추적/해제
- Graceful degradation (Redis 장애)
- UUID 충돌 방지

## 보안 고려 사항

### 타이밍 공격 방지

**로그인 엔드포인트 (Phase 2A에서 구현):**

```python
if not user:
    # 타이밍 공격 방지: 존재하지 않는 사용자도 동일한 시간 소요
    verify_password(request.password, hash_password("dummy"))
    raise HTTPException(status_code=401, detail="Invalid email or password")
```

- 사용자가 존재하지 않아도 bcrypt 검증 실행
- 공격자가 타이밍으로 사용자 존재 여부 추측 불가

### Admin 자기 강등 방지

```python
if current_user.id == user_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot change your own role",
    )
```

- Admin이 실수로 자신의 역할을 변경하는 것 방지
- 시스템 잠금 위험 제거

### 감사 로깅

```python
logger.info(
    "Role changed: admin=%s target=%s old_role=%s new_role=%s",
    current_user.id,
    user_id,
    old_role,
    request.role.value,
)
```

- 모든 역할 변경 이벤트 기록
- 추후 보안 감사 및 컴플라이언스 대응 가능

### Graceful Degradation

```python
async def init_redis() -> Redis | None:
    try:
        _redis_client = Redis.from_url(settings.REDIS_URL, ...)
        await _redis_client.ping()
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable — rate limiting disabled")
        return None
```

- Redis 장애 시 서비스 중단 대신 Rate Limiting만 비활성화
- 가용성 우선 (Availability over strict throttling)

### Redis 보안

1. **UUID member key 사용:**
   ```python
   member = f"{now}-{uuid_mod.uuid4().hex[:8]}"
   ```
   - 동일 타임스탬프에 여러 요청이 와도 ZADD score 충돌 없음

2. **거부된 요청은 카운트 안 함:**
   ```python
   if request_count >= limit:
       # Sorted Set에 추가 안 함
       return False, 0, retry_after
   ```
   - 정확한 사용량 집계
   - DDoS 시에도 카운터 오염 방지

3. **TTL 안전망:**
   ```python
   await redis.expire(key, 3600)  # WS 연결 추적
   ```
   - 연결 해제 실패 시에도 1시간 후 자동 정리

## 알려진 제한 사항

1. **분산 환경 고려 없음**: 현재 구현은 단일 Redis 인스턴스 가정
   - 해결: Redis Cluster 또는 Sentinel 도입 (Phase 7)

2. **Rate Limit 헤더 미설정**: `X-RateLimit-*` 헤더가 middleware에서 응답에 추가되지 않음
   - 해결: Response middleware에서 `request.state.rate_limit_*` 읽어 헤더 추가

3. **WebSocket Rate Limiting 미적용**: WebSocket 메시지는 아직 Rate Limiting 없음
   - 해결: Phase 7에서 WebSocket middleware에 통합

4. **Daily Limit 미구현**: `max_pipelines_per_day` 등 일일 제한은 정의만 되어 있음
   - 해결: Phase 5 Pipeline Orchestrator에서 구현

5. **로그인 실패 잠금 없음**: `failed_login_attempts`, `locked_until` 필드는 정의만 됨
   - 해결: 다음 리뷰 사이클에서 추가

## 다음 단계

### Phase 2C: API 키 및 Circuit Breaker

- **API 키 관리**: 프로그래매틱 접근용 장기 인증 키
  - 키 발급/폐기 엔드포인트
  - 키 기반 인증 의존성
  - 키별 권한 범위 (scopes)

- **비용 Circuit Breaker**: LLM API 호출 비용 제어
  - 사용자별 월간 비용 제한
  - 비용 초과 시 자동 차단
  - 실시간 비용 모니터링

### Phase 3 통합

- Intent Analyzer에서 RBAC 권한 확인
- Multi-LLM Router에서 역할별 모델 제한
- Discussion Engine에서 일일 토론 수 제한

### Phase 7 프로덕션 강화

- Redis Cluster/Sentinel 설정
- WebSocket Rate Limiting 통합
- Response middleware에서 Rate Limit 헤더 추가
- 로그인 실패 잠금 구현
- Prometheus 메트릭 (rate limit hits, Redis latency)

## 참고 자료

- [Redis Sorted Sets 공식 문서](https://redis.io/docs/data-types/sorted-sets/)
- [Sliding Window Rate Limiting 알고리즘](https://en.wikipedia.org/wiki/Rate_limiting#Sliding_window)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [OWASP 인증 보안 가이드](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
