"""Unit tests for RBAC (Role-Based Access Control) permissions."""

import uuid

import pytest

from backend.gateway.auth import create_access_token, hash_password
from backend.gateway.rbac import ROLE_PERMISSIONS, get_permission, is_unlimited
from backend.shared.models import User, UserRole


class TestUserRoleEnum:
    """Tests for UserRole enum values."""

    def test_free_role_value(self):
        """Test that FREE role has correct string value."""
        assert UserRole.FREE.value == "free"

    def test_pro_role_value(self):
        """Test that PRO role has correct string value."""
        assert UserRole.PRO.value == "pro"

    def test_admin_role_value(self):
        """Test that ADMIN role has correct string value."""
        assert UserRole.ADMIN.value == "admin"

    def test_role_count(self):
        """Test that there are exactly 3 roles."""
        assert len(UserRole) == 3

    def test_role_is_string_enum(self):
        """Test that UserRole members are strings."""
        for role in UserRole:
            assert isinstance(role.value, str)

    def test_role_from_value(self):
        """Test creating UserRole from string value."""
        assert UserRole("free") == UserRole.FREE
        assert UserRole("pro") == UserRole.PRO
        assert UserRole("admin") == UserRole.ADMIN

    def test_invalid_role_value_raises(self):
        """Test that invalid role value raises ValueError."""
        with pytest.raises(ValueError):
            UserRole("invalid")


class TestRolePermissions:
    """Tests for ROLE_PERMISSIONS dictionary."""

    def test_all_roles_have_permissions(self):
        """Test that ROLE_PERMISSIONS has entries for all UserRole values."""
        for role in UserRole:
            assert role in ROLE_PERMISSIONS, f"Missing permissions for role: {role}"

    def test_no_extra_roles_in_permissions(self):
        """Test that ROLE_PERMISSIONS has no extra entries beyond defined roles."""
        for role_key in ROLE_PERMISSIONS:
            assert role_key in UserRole, f"Extra role in permissions: {role_key}"

    def test_all_roles_have_same_permission_keys(self):
        """Test that all roles define the same set of permission keys."""
        all_keys = [set(perms.keys()) for perms in ROLE_PERMISSIONS.values()]
        for keys in all_keys:
            assert keys == all_keys[0], "Permission keys differ across roles"

    def test_expected_permission_keys(self):
        """Test that expected permission keys exist."""
        expected_keys = {
            "max_pipelines_per_day",
            "max_discussions_per_day",
            "max_requests_per_minute",
            "ws_max_message_size",
            "ws_max_connections",
        }
        for role in UserRole:
            assert set(ROLE_PERMISSIONS[role].keys()) == expected_keys

    def test_all_permission_values_are_integers(self):
        """Test that all permission values are integers."""
        for role in UserRole:
            for key, value in ROLE_PERMISSIONS[role].items():
                assert isinstance(value, int), (
                    f"Non-integer permission: {role}.{key} = {value}"
                )


class TestFreeRoleLimits:
    """Tests for FREE role permission limits."""

    def test_max_pipelines_per_day(self):
        """Test FREE role pipeline limit."""
        assert ROLE_PERMISSIONS[UserRole.FREE]["max_pipelines_per_day"] == 3

    def test_max_discussions_per_day(self):
        """Test FREE role discussion limit."""
        assert ROLE_PERMISSIONS[UserRole.FREE]["max_discussions_per_day"] == 10

    def test_max_requests_per_minute(self):
        """Test FREE role request rate limit."""
        assert ROLE_PERMISSIONS[UserRole.FREE]["max_requests_per_minute"] == 10

    def test_ws_max_message_size(self):
        """Test FREE role WebSocket message size limit (4KB)."""
        assert ROLE_PERMISSIONS[UserRole.FREE]["ws_max_message_size"] == 4096

    def test_ws_max_connections(self):
        """Test FREE role WebSocket connection limit."""
        assert ROLE_PERMISSIONS[UserRole.FREE]["ws_max_connections"] == 2

    def test_free_has_no_unlimited_key_limits(self):
        """Test that FREE role has no unlimited (-1) permissions for key limits."""
        key_limits = [
            "max_pipelines_per_day",
            "max_requests_per_minute",
            "ws_max_connections",
        ]
        for key in key_limits:
            assert ROLE_PERMISSIONS[UserRole.FREE][key] > 0, (
                f"FREE role should not have unlimited {key}"
            )


class TestProRoleLimits:
    """Tests for PRO role permission limits."""

    def test_max_pipelines_per_day(self):
        """Test PRO role pipeline limit."""
        assert ROLE_PERMISSIONS[UserRole.PRO]["max_pipelines_per_day"] == 100

    def test_max_discussions_per_day(self):
        """Test PRO role has unlimited discussions."""
        assert ROLE_PERMISSIONS[UserRole.PRO]["max_discussions_per_day"] == -1

    def test_max_requests_per_minute(self):
        """Test PRO role request rate limit."""
        assert ROLE_PERMISSIONS[UserRole.PRO]["max_requests_per_minute"] == 60

    def test_ws_max_message_size(self):
        """Test PRO role WebSocket message size limit (64KB)."""
        assert ROLE_PERMISSIONS[UserRole.PRO]["ws_max_message_size"] == 65536

    def test_ws_max_connections(self):
        """Test PRO role WebSocket connection limit."""
        assert ROLE_PERMISSIONS[UserRole.PRO]["ws_max_connections"] == 10


class TestAdminRoleLimits:
    """Tests for ADMIN role permission limits."""

    def test_max_pipelines_per_day_unlimited(self):
        """Test ADMIN role has unlimited pipelines."""
        assert ROLE_PERMISSIONS[UserRole.ADMIN]["max_pipelines_per_day"] == -1

    def test_max_discussions_per_day_unlimited(self):
        """Test ADMIN role has unlimited discussions."""
        assert ROLE_PERMISSIONS[UserRole.ADMIN]["max_discussions_per_day"] == -1

    def test_max_requests_per_minute_unlimited(self):
        """Test ADMIN role has unlimited request rate."""
        assert ROLE_PERMISSIONS[UserRole.ADMIN]["max_requests_per_minute"] == -1

    def test_ws_max_message_size(self):
        """Test ADMIN role WebSocket message size limit (1MB)."""
        assert ROLE_PERMISSIONS[UserRole.ADMIN]["ws_max_message_size"] == 1048576

    def test_ws_max_connections_unlimited(self):
        """Test ADMIN role has unlimited WebSocket connections."""
        assert ROLE_PERMISSIONS[UserRole.ADMIN]["ws_max_connections"] == -1


class TestRoleHierarchy:
    """Tests for role hierarchy (admin > pro > free)."""

    def test_pipelines_hierarchy(self):
        """Test that pipeline limits increase with role tier."""
        free_limit = ROLE_PERMISSIONS[UserRole.FREE]["max_pipelines_per_day"]
        pro_limit = ROLE_PERMISSIONS[UserRole.PRO]["max_pipelines_per_day"]
        admin_limit = ROLE_PERMISSIONS[UserRole.ADMIN]["max_pipelines_per_day"]

        assert free_limit < pro_limit
        assert is_unlimited(admin_limit)

    def test_requests_per_minute_hierarchy(self):
        """Test that request rate limits increase with role tier."""
        free_limit = ROLE_PERMISSIONS[UserRole.FREE]["max_requests_per_minute"]
        pro_limit = ROLE_PERMISSIONS[UserRole.PRO]["max_requests_per_minute"]
        admin_limit = ROLE_PERMISSIONS[UserRole.ADMIN]["max_requests_per_minute"]

        assert free_limit < pro_limit
        assert is_unlimited(admin_limit)

    def test_ws_message_size_hierarchy(self):
        """Test that WebSocket message size limits increase with role tier."""
        free_limit = ROLE_PERMISSIONS[UserRole.FREE]["ws_max_message_size"]
        pro_limit = ROLE_PERMISSIONS[UserRole.PRO]["ws_max_message_size"]
        admin_limit = ROLE_PERMISSIONS[UserRole.ADMIN]["ws_max_message_size"]

        assert free_limit < pro_limit
        assert pro_limit < admin_limit

    def test_ws_connections_hierarchy(self):
        """Test that WebSocket connection limits increase with role tier."""
        free_limit = ROLE_PERMISSIONS[UserRole.FREE]["ws_max_connections"]
        pro_limit = ROLE_PERMISSIONS[UserRole.PRO]["ws_max_connections"]
        admin_limit = ROLE_PERMISSIONS[UserRole.ADMIN]["ws_max_connections"]

        assert free_limit < pro_limit
        assert is_unlimited(admin_limit)


class TestGetPermission:
    """Tests for get_permission function."""

    def test_get_free_permission(self):
        """Test getting a permission for FREE role."""
        result = get_permission(UserRole.FREE, "max_pipelines_per_day")
        assert result == 3

    def test_get_pro_permission(self):
        """Test getting a permission for PRO role."""
        result = get_permission(UserRole.PRO, "max_requests_per_minute")
        assert result == 60

    def test_get_admin_unlimited_permission(self):
        """Test getting an unlimited permission for ADMIN role."""
        result = get_permission(UserRole.ADMIN, "max_pipelines_per_day")
        assert result == -1

    def test_get_all_permissions_for_each_role(self):
        """Test getting every permission for every role."""
        for role in UserRole:
            for key in ROLE_PERMISSIONS[role]:
                result = get_permission(role, key)
                assert result == ROLE_PERMISSIONS[role][key]

    def test_invalid_permission_key_raises(self):
        """Test that invalid permission key raises KeyError."""
        with pytest.raises(KeyError, match="Unknown permission"):
            get_permission(UserRole.FREE, "nonexistent_permission")


class TestIsUnlimited:
    """Tests for is_unlimited function."""

    def test_negative_one_is_unlimited(self):
        """Test that -1 is unlimited."""
        assert is_unlimited(-1) is True

    def test_zero_is_not_unlimited(self):
        """Test that 0 is not unlimited."""
        assert is_unlimited(0) is False

    def test_positive_is_not_unlimited(self):
        """Test that positive values are not unlimited."""
        assert is_unlimited(1) is False
        assert is_unlimited(100) is False
        assert is_unlimited(999999) is False

    def test_other_negative_is_not_unlimited(self):
        """Test that negative values other than -1 are not unlimited."""
        assert is_unlimited(-2) is False
        assert is_unlimited(-100) is False


class TestRequireRoleDependency:
    """Tests for require_role dependency via API endpoints."""

    @pytest.mark.asyncio
    async def test_admin_can_update_role(self, client, test_session):
        """Test that admin user can update another user's role."""
        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            email="admin_rbac@example.com",
            hashed_password=hash_password("AdminPass123"),
            display_name="Admin RBAC",
            role=UserRole.ADMIN,
        )
        test_session.add(admin_user)

        # Create target user
        target_user = User(
            id=uuid.uuid4(),
            email="target_rbac@example.com",
            hashed_password=hash_password("TargetPass123"),
            display_name="Target RBAC",
            role=UserRole.FREE,
        )
        test_session.add(target_user)
        await test_session.commit()

        admin_token = create_access_token(str(admin_user.id), admin_user.role.value)

        response = await client.put(
            f"/api/v1/auth/users/{target_user.id}/role",
            json={"role": "pro"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "pro"

    @pytest.mark.asyncio
    async def test_free_user_cannot_update_role(self, client, test_session):
        """Test that free user cannot update another user's role."""
        # Create free user
        free_user = User(
            id=uuid.uuid4(),
            email="free_rbac@example.com",
            hashed_password=hash_password("FreePass123"),
            display_name="Free RBAC",
            role=UserRole.FREE,
        )
        test_session.add(free_user)

        # Create target user
        target_user = User(
            id=uuid.uuid4(),
            email="target2_rbac@example.com",
            hashed_password=hash_password("TargetPass123"),
            display_name="Target2 RBAC",
            role=UserRole.FREE,
        )
        test_session.add(target_user)
        await test_session.commit()

        free_token = create_access_token(str(free_user.id), free_user.role.value)

        response = await client.put(
            f"/api/v1/auth/users/{target_user.id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {free_token}"},
        )
        assert response.status_code == 403
        data = response.json()
        assert "insufficient permissions" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_pro_user_cannot_update_role(self, client, test_session):
        """Test that pro user cannot update another user's role."""
        pro_user = User(
            id=uuid.uuid4(),
            email="pro_rbac@example.com",
            hashed_password=hash_password("ProPass123"),
            display_name="Pro RBAC",
            role=UserRole.PRO,
        )
        test_session.add(pro_user)

        target_user = User(
            id=uuid.uuid4(),
            email="target3_rbac@example.com",
            hashed_password=hash_password("TargetPass123"),
            display_name="Target3 RBAC",
            role=UserRole.FREE,
        )
        test_session.add(target_user)
        await test_session.commit()

        pro_token = create_access_token(str(pro_user.id), pro_user.role.value)

        response = await client.put(
            f"/api/v1/auth/users/{target_user.id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {pro_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_role_without_auth(self, client):
        """Test that role update requires authentication."""
        fake_user_id = uuid.uuid4()
        response = await client.put(
            f"/api/v1/auth/users/{fake_user_id}/role",
            json={"role": "admin"},
        )
        assert response.status_code == 403  # HTTPBearer returns 403 when no token

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_role(self, client, test_session):
        """Test updating role for non-existent user returns 404."""
        admin_user = User(
            id=uuid.uuid4(),
            email="admin2_rbac@example.com",
            hashed_password=hash_password("AdminPass123"),
            display_name="Admin2 RBAC",
            role=UserRole.ADMIN,
        )
        test_session.add(admin_user)
        await test_session.commit()

        admin_token = create_access_token(str(admin_user.id), admin_user.role.value)
        fake_user_id = uuid.uuid4()

        response = await client.put(
            f"/api/v1/auth/users/{fake_user_id}/role",
            json={"role": "pro"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_role_invalid_role_value(self, client, test_session):
        """Test updating role with invalid role value returns 422."""
        admin_user = User(
            id=uuid.uuid4(),
            email="admin3_rbac@example.com",
            hashed_password=hash_password("AdminPass123"),
            display_name="Admin3 RBAC",
            role=UserRole.ADMIN,
        )
        test_session.add(admin_user)

        target_user = User(
            id=uuid.uuid4(),
            email="target4_rbac@example.com",
            hashed_password=hash_password("TargetPass123"),
            display_name="Target4 RBAC",
            role=UserRole.FREE,
        )
        test_session.add(target_user)
        await test_session.commit()

        admin_token = create_access_token(str(admin_user.id), admin_user.role.value)

        response = await client.put(
            f"/api/v1/auth/users/{target_user.id}/role",
            json={"role": "superadmin"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_me_endpoint_returns_role(self, client, test_session):
        """Test that /me endpoint includes user role."""
        user = User(
            id=uuid.uuid4(),
            email="role_me@example.com",
            hashed_password=hash_password("TestPass123"),
            display_name="Role Me",
            role=UserRole.PRO,
        )
        test_session.add(user)
        await test_session.commit()

        token = create_access_token(str(user.id), user.role.value)
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "pro"

    @pytest.mark.asyncio
    async def test_register_creates_free_role(self, client):
        """Test that new registration always creates FREE role user."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new_rbac@example.com",
                "password": "NewPass123",
                "display_name": "New RBAC User",
            },
        )
        assert response.status_code == 201

        # Verify role via /me
        access_token = response.json()["access_token"]
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.json()["role"] == "free"
