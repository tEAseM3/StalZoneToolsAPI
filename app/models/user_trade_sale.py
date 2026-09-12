from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user_trade_position import UserTradePosition


class UserTradeSale(Base):
    __tablename__ = "user_trade_sales"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    position_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_trade_positions.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    position: Mapped[UserTradePosition] = relationship(back_populates="sales")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_user_trade_sale_quantity"),
        CheckConstraint("revenue_total >= 0", name="check_user_trade_sale_revenue_total"),
        Index("idx_user_trade_sales_position", "position_id"),
    )
