from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class HCP(TimestampMixin, Base):
    __tablename__ = 'hcp'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doctor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hospital: Mapped[str] = mapped_column(String(255), nullable=False)
    speciality: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    history_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    interactions = relationship('Interaction', back_populates='hcp')
