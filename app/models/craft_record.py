from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.craft_sale import CraftSale
    from app.models.user import User


class CraftRecord(Base):
    __tablename__ = "craft_records"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    cost_source: Mapped[str] = mapped_column(String(16), nullable=False)
    market_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="craft_records")
    sales: Mapped[list[CraftSale]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("length(trim(item_id)) > 0", name="check_craft_record_item_id_length"),
        CheckConstraint("length(trim(item_name)) > 0", name="check_craft_record_item_name_length"),
        CheckConstraint("quantity > 0", name="check_craft_record_quantity"),
        CheckConstraint("unit_cost >= 0", name="check_craft_record_unit_cost"),
        CheckConstraint("market_unit_price >= 0", name="check_craft_record_market_price"),
        CheckConstraint(
            "cost_source IN ('recipe', 'market')", name="check_craft_record_cost_source"
        ),
        Index("idx_craft_records_user_item", "user_id", "item_name"),
    )
