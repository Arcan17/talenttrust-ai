"""Role-based access control dependency.

Usage in a router:
    @router.post(..., dependencies=[Depends(require_role(Role.org_admin))])
or to receive the user:
    user: User = Depends(require_role(Role.org_admin, Role.recruiter))
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import Role, User


def require_role(*allowed: Role) -> Callable[..., Awaitable[User]]:
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if allowed and user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this action",
            )
        return user

    return _dep
