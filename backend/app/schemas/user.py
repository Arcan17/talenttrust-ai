"""User response schema."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    email: EmailStr
    role: Role
    is_active: bool
