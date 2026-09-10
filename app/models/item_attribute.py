from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.item import Item


class ItemAttribute(Base):
    __tablename__ = "item_attributes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    item: Mapped[Item] = relationship(back_populates="attributes")

    __table_args__ = (
        CheckConstraint("length(trim(key)) > 0", name="check_item_attribute_key_length"),
        CheckConstraint("sort_order >= 0", name="check_item_attribute_sort_order"),
        CheckConstraint(
            "value_text IS NOT NULL OR value_numeric IS NOT NULL",
            name="check_item_attribute_has_value",
        ),
    )
