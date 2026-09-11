from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HideoutPerk(Base):
    __tablename__ = "hideout_perks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="check_hideout_perk_id_length"),
        CheckConstraint("length(trim(name)) > 0", name="check_hideout_perk_name_length"),
    )
