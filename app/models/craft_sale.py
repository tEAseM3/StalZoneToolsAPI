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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.craft_record import CraftRecord


class CraftSale(Base):
    __tablename__ = "craft_sales"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("craft_records.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    record: Mapped[CraftRecord] = relationship(back_populates="sales")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_craft_sale_quantity"),
        CheckConstraint("unit_price >= 0", name="check_craft_sale_unit_price"),
        Index("idx_craft_sales_record", "record_id"),
    )
