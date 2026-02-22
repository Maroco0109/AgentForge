"""Role-based access control (RBAC) permissions."""

from backend.shared.models import UserRole

# Permission limits per role
# -1 means unlimited
ROLE_PERMISSIONS: dict[UserRole, dict[str, int | float]] = {
    UserRole.FREE: {
        "max_pipelines_per_day": 3,
        "max_discussions_per_day": 10,
        "max_requests_per_minute": 10,
        "ws_max_message_size": 4096,  # 4KB
        "ws_max_connections": 2,
        "max_cost_per_day_usd": 1.0,
    },
    UserRole.PRO: {
        "max_pipelines_per_day": 100,
        "max_discussions_per_day": -1,  # unlimited
        "max_requests_per_minute": 60,
        "ws_max_message_size": 65536,  # 64KB
        "ws_max_connections": 10,
        "max_cost_per_day_usd": 50.0,
    },
    UserRole.ADMIN: {
        "max_pipelines_per_day": -1,
        "max_discussions_per_day": -1,
        "max_requests_per_minute": -1,
        "ws_max_message_size": 1048576,  # 1MB
        "ws_max_connections": -1,
        "max_cost_per_day_usd": -1,
    },
}


def get_permission(role: UserRole, permission: str) -> int | float:
    """Get a specific permission value for a role.

    Args:
        role: The user's role.
        permission: The permission key to look up.

    Returns:
        The permission value (-1 means unlimited).

    Raises:
        KeyError: If the permission key is invalid.
    """
    role_perms = ROLE_PERMISSIONS.get(role)
    if role_perms is None:
        raise KeyError(f"Unknown role: {role}")
    if permission not in role_perms:
        raise KeyError(f"Unknown permission: {permission}")
    return role_perms[permission]


def is_unlimited(value: int | float) -> bool:
    """Check if a permission value represents unlimited access."""
    return value == -1
