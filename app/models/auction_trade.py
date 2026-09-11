from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuctionTrade(Base):
    __tablename__ = "auction_trades"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    region: Mapped[str] = mapped_column(String(3), nullable=False)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_trade_region"
        ),
        CheckConstraint("length(trim(item_id)) > 0", name="check_auction_trade_item_id_length"),
        CheckConstraint("amount > 0", name="check_auction_trade_amount"),
        CheckConstraint("lot_price >= 0", name="check_auction_trade_lot_price"),
        CheckConstraint("unit_price >= 0", name="check_auction_trade_unit_price"),
        CheckConstraint(
            "length(trim(source_fingerprint)) > 0", name="check_auction_trade_fingerprint_length"
        ),
        Index("idx_auction_trades_region_item_sold_at", "region", "item_id", "sold_at"),
    )
