from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(55), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    user_role: Mapped[list[UserRole]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    role_permission: Mapped[list[RolePermission]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="check_role_name_length"),
        CheckConstraint("length(trim(description)) < 2000", name="check_role_description_length"),
    )
