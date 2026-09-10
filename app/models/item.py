from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.item_attribute import ItemAttribute


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(55), nullable=True)
    status_state: Mapped[str | None] = mapped_column(String(55), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    attributes: Mapped[list[ItemAttribute]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="check_item_id_length"),
        CheckConstraint("length(trim(source_path)) > 0", name="check_item_source_path_length"),
        CheckConstraint("length(trim(category)) > 0", name="check_item_category_length"),
        CheckConstraint("length(trim(name)) > 0", name="check_item_name_length"),
        CheckConstraint("length(trim(source_sha)) > 0", name="check_item_source_sha_length"),
    )
