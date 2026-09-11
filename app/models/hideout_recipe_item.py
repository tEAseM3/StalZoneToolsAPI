from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hideout_recipe import HideoutRecipe


class HideoutRecipeItem(Base):
    __tablename__ = "hideout_recipe_items"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("hideout_recipes.id", ondelete="CASCADE"), nullable=False
    )
    component_type: Mapped[str] = mapped_column(String(16), nullable=False)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    recipe: Mapped[HideoutRecipe] = relationship(back_populates="components")

    __table_args__ = (
        CheckConstraint(
            "component_type IN ('ingredient', 'result')",
            name="check_hideout_recipe_item_component_type",
        ),
        CheckConstraint("length(trim(item_id)) > 0", name="check_hideout_recipe_item_id_length"),
        CheckConstraint("amount > 0", name="check_hideout_recipe_item_amount"),
        CheckConstraint("sort_order >= 0", name="check_hideout_recipe_item_sort_order"),
        Index("idx_hideout_recipe_items_recipe", "recipe_id"),
        Index("idx_hideout_recipe_items_item", "item_id"),
    )
