from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hideout_recipe import HideoutRecipe


class CraftProfitSnapshot(Base):
    __tablename__ = "craft_profit_snapshots"

    recipe_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("hideout_recipes.id", ondelete="CASCADE"), primary_key=True
    )
    region: Mapped[str] = mapped_column(String(3), primary_key=True)
    result_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    ingredients_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    energy_required: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    energy_item_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    energy_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    has_complete_prices: Mapped[bool] = mapped_column(Boolean, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    recipe: Mapped[HideoutRecipe] = relationship(back_populates="profit_snapshots")

    __table_args__ = (
        CheckConstraint(
            "region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_craft_profit_snapshot_region"
        ),
        CheckConstraint("energy_required >= 0", name="check_craft_profit_energy_required"),
        CheckConstraint("energy_item_amount >= 0", name="check_craft_profit_energy_item_amount"),
        Index("idx_craft_profit_snapshots_region_profit", "region", "profit"),
    )
