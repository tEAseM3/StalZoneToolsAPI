from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuctionPriceCandle(Base):
    __tablename__ = "auction_price_candles"

    region: Mapped[str] = mapped_column(String(3), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    interval: Mapped[str] = mapped_column(String(8), primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    median_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    vwap_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    min_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    max_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    percentile_10_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    percentile_90_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    turnover: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_candle_region"
        ),
        CheckConstraint("length(trim(item_id)) > 0", name="check_auction_candle_item_id_length"),
        CheckConstraint("interval IN ('day', 'week')", name="check_auction_candle_interval"),
        CheckConstraint("median_unit_price >= 0", name="check_auction_candle_median"),
        CheckConstraint("vwap_unit_price >= 0", name="check_auction_candle_vwap"),
        CheckConstraint("min_unit_price >= 0", name="check_auction_candle_min"),
        CheckConstraint("max_unit_price >= 0", name="check_auction_candle_max"),
        CheckConstraint("trade_count >= 0", name="check_auction_candle_trade_count"),
        CheckConstraint("volume >= 0", name="check_auction_candle_volume"),
        CheckConstraint("turnover >= 0", name="check_auction_candle_turnover"),
        Index("idx_auction_price_candles_region_item_interval", "region", "item_id", "interval"),
    )
