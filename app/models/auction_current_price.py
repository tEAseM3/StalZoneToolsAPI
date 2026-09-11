from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuctionCurrentPrice(Base):
    __tablename__ = "auction_current_prices"

    region: Mapped[str] = mapped_column(String(3), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    best_buyout_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    best_bid_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    lots_total: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_current_price_region"
        ),
        CheckConstraint(
            "length(trim(item_id)) > 0", name="check_auction_current_price_item_id_length"
        ),
        CheckConstraint("best_buyout_unit_price >= 0", name="check_auction_buyout_unit_price"),
        CheckConstraint("best_bid_unit_price >= 0", name="check_auction_bid_unit_price"),
        CheckConstraint("lots_total >= 0", name="check_auction_lots_total"),
        Index("idx_auction_current_prices_region_observed", "region", "observed_at"),
    )
