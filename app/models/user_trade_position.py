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
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.user_trade_sale import UserTradeSale


class UserTradePosition(Base):
    __tablename__ = "user_trade_positions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(3), nullable=False)
    purchased_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="trade_positions")
    sales: Mapped[list[UserTradeSale]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(item_id)) > 0", name="check_user_trade_position_item_id_length"
        ),
        CheckConstraint(
            "length(trim(item_name)) > 0", name="check_user_trade_position_item_name_length"
        ),
        CheckConstraint(
            "region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')",
            name="check_user_trade_position_region",
        ),
        CheckConstraint("purchased_quantity > 0", name="check_user_trade_position_quantity"),
        CheckConstraint("purchase_total >= 0", name="check_user_trade_position_purchase_total"),
        Index("idx_user_trade_positions_user_region", "user_id", "region"),
    )
