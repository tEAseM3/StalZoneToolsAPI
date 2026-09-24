from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuctionRefreshQueue(Base):
    __tablename__ = "auction_refresh_queue"

    region: Mapped[str] = mapped_column(String(3), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    next_lots_refresh_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_history_refresh_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_lots_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_history_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    market_state: Mapped[str] = mapped_column(String(16), nullable=False, default="probing")
    empty_probe_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_lots_was_empty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_refresh_queue_region"
        ),
        CheckConstraint(
            "length(trim(item_id)) > 0", name="check_auction_refresh_queue_item_id_length"
        ),
        CheckConstraint("priority >= 0", name="check_auction_refresh_queue_priority"),
        CheckConstraint(
            "market_state IN ('probing', 'active', 'retired')",
            name="check_auction_refresh_queue_market_state",
        ),
        CheckConstraint(
            "empty_probe_count >= 0", name="check_auction_refresh_queue_empty_probe_count"
        ),
    )
