from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Interaction(TimestampMixin, Base):
    __tablename__ = 'interaction'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    hcp_id: Mapped[int | None] = mapped_column(ForeignKey('hcp.id', ondelete='SET NULL'))
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    interaction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    discussion_notes: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='logged')

    hcp = relationship('HCP', back_populates='interactions')
    user = relationship('User', back_populates='interactions')
    products = relationship('InteractionProduct', back_populates='interaction', cascade='all, delete-orphan')
    attachments = relationship('Attachment', back_populates='interaction', cascade='all, delete-orphan')
    activity_logs = relationship('ActivityLog', back_populates='interaction', cascade='all, delete-orphan')


class InteractionProduct(TimestampMixin, Base):
    __tablename__ = 'interaction_product'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey('interaction.id', ondelete='CASCADE'), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    interaction = relationship('Interaction', back_populates='products')


class Attachment(TimestampMixin, Base):
    __tablename__ = 'attachments'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey('interaction.id', ondelete='CASCADE'), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)

    interaction = relationship('Interaction', back_populates='attachments')


class ActivityLog(TimestampMixin, Base):
    __tablename__ = 'activity_log'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interaction_id: Mapped[int | None] = mapped_column(ForeignKey('interaction.id', ondelete='SET NULL'))
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    interaction = relationship('Interaction', back_populates='activity_logs')
    user = relationship('User', back_populates='activity_logs')
