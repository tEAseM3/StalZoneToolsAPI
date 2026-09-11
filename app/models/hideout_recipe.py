from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hideout_recipe_item import HideoutRecipeItem


class HideoutRecipe(Base):
    __tablename__ = "hideout_recipes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source_index: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    bench: Mapped[str] = mapped_column(String(64), nullable=False)
    category_key: Mapped[str] = mapped_column(String(255), nullable=False)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subcategory_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subcategory_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    energy: Mapped[float] = mapped_column(Numeric, nullable=False)
    required_perks: Mapped[dict] = mapped_column(JSONB, nullable=False)
    required_features: Mapped[list] = mapped_column(JSONB, nullable=False)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    components: Mapped[list[HideoutRecipeItem]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("source_index >= 0", name="check_hideout_recipe_source_index"),
        CheckConstraint("length(trim(bench)) > 0", name="check_hideout_recipe_bench_length"),
        CheckConstraint(
            "length(trim(category_key)) > 0", name="check_hideout_recipe_category_key_length"
        ),
        CheckConstraint(
            "length(trim(category_name)) > 0", name="check_hideout_recipe_category_name_length"
        ),
        CheckConstraint("energy >= 0", name="check_hideout_recipe_energy"),
        CheckConstraint(
            "length(trim(source_sha)) > 0", name="check_hideout_recipe_source_sha_length"
        ),
        Index("idx_hideout_recipes_bench", "bench"),
        Index("idx_hideout_recipes_category_key", "category_key"),
        Index("idx_hideout_recipes_subcategory_key", "subcategory_key"),
        Index("idx_hideout_recipes_raw_gin", "raw", postgresql_using="gin"),
    )
